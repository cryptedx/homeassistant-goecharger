"""go-eCharger API adapters."""

from __future__ import annotations

import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .const import API_VERSION_V1, API_VERSION_V2, DEFAULT_API_VERSION


V2_NUMBERS = {
    "amp": {"name": "Requested current", "attribute": "charger_max_current", "unit": "A", "min": 6, "max": 32, "step": 1},
    "ama": {"name": "Absolute max current", "attribute": "charger_absolute_max_current", "unit": "A", "min": 6, "max": 32, "step": 1},
    "dwo": {"name": "Charge limit", "attribute": "charge_limit", "unit": "kWh", "min": 0, "max": 100, "step": 0.1},
    "mca": {"name": "Minimum charging current", "unit": "A", "min": 6, "max": 32, "step": 1},
    "fst": {"name": "Starting power", "unit": "W", "min": 0, "max": 22000, "step": 100},
    "pgt": {"name": "Grid target power", "unit": "W", "min": -22000, "max": 22000, "step": 100},
    "zfo": {"name": "Zero feed-in offset", "unit": "W", "min": -10000, "max": 10000, "step": 10},
}

V2_SELECTS = {
    "frc": {"name": "Force state", "attribute": "force_state", "options": {"Neutral": 0, "Off": 1, "On": 2}},
    "ust": {"name": "Cable lock mode", "attribute": "cable_lock_mode", "options": {"Normal": 0, "Auto unlock": 1, "Always lock": 2}},
    "lmo": {"name": "Logic mode", "attribute": "logic_mode", "options": {"Default": 3, "Awattar": 4, "Automatic stop": 5}},
    "acs": {"name": "Access control", "attribute": "access_control", "options": {"Open": 0, "Wait": 1}},
    "pwm": {"name": "Phase wish mode", "attribute": "phase_wish_mode", "options": {"Force 3": 0, "Wish 1": 1, "Wish 3": 2}},
}

V2_SWITCHES = {
    "fup": {"name": "Use PV surplus", "attribute": "pv_surplus"},
    "awe": {"name": "Use Awattar", "attribute": "awattar"},
    "fzf": {"name": "Zero feed-in", "attribute": "zero_feed_in"},
    "su": {"name": "Simulate unplugging short", "attribute": "simulate_unplugging_short"},
    "sua": {"name": "Simulate unplugging always", "attribute": "simulate_unplugging_always"},
}


class GoeChargerV1:
    def __init__(self, host):
        from goecharger import GoeCharger

        self._charger = GoeCharger(host)

    def requestStatus(self):
        return self._charger.requestStatus()

    def setTmpMaxCurrent(self, current):
        return self._charger.setTmpMaxCurrent(current)

    def setAbsoluteMaxCurrent(self, current):
        return self._charger.setAbsoluteMaxCurrent(current)

    def setCableLockMode(self, mode):
        from goecharger import GoeCharger

        modes = (
            GoeCharger.CableLockMode.UNLOCKCARFIRST,
            GoeCharger.CableLockMode.AUTOMATIC,
            GoeCharger.CableLockMode.LOCKED,
        )
        return self._charger.setCableLockMode(modes[max(0, min(int(mode), 2))])

    def setChargeLimit(self, chargeLimit):
        return self._charger.setChargeLimit(chargeLimit)

    def setAllowCharging(self, allow):
        return self._charger.setAllowCharging(allow)

    def setApiKey(self, key, value):
        raise ValueError("Raw API-key writes require API v2")


class GoeChargerV2:
    FILTER_KEYS = (
        "acs",
        "acu",
        "adi",
        "alw",
        "ama",
        "amp",
        "awe",
        "car",
        "cbl",
        "dwo",
        "err",
        "eto",
        "frc",
        "fsp",
        "fst",
        "fup",
        "fwv",
        "fzf",
        "lmo",
        "mca",
        "modelStatus",
        "nrg",
        "pakku",
        "pgrid",
        "ppv",
        "pwm",
        "sse",
        "su",
        "sua",
        "tds",
        "tma",
        "tof",
        "trx",
        "ust",
        "wh",
        "wst",
        "zfo",
    )
    CAR_STATUS = {
        1: "Charger ready, no vehicle",
        2: "charging",
        3: "Waiting for vehicle",
        4: "charging finished, vehicle still connected",
    }
    ERR = {0: "OK", 1: "RCCB", 3: "PHASE", 8: "NO_GROUND", 10: "INTERNAL"}
    ACCESS = {0: "free", 1: "rfid/app"}

    def __init__(self, host, open_url=urlopen):
        if not host:
            raise ValueError("host must be specified")
        self.host = host
        self._open_url = open_url

    def _get_json(self, path, params):
        url = f"http://{self.host}{path}?{urlencode(params, safe=',')}"
        with self._open_url(Request(url), timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))

    def _set(self, key, value):
        return self._get_json("/api/set", {key: json.dumps(value)})

    def _clamp_current(self, current):
        return max(6, min(int(current), 32))

    def requestStatus(self):
        status = self._get_json("/api/status", {"filter": ",".join(self.FILTER_KEYS)})
        nrg = status.get("nrg") or []
        tma = status.get("tma") or []

        def value(values, index, default=0):
            return values[index] if len(values) > index else default

        def kwh(raw):
            return None if raw is None else round(float(raw) / 1000.0, 5)

        data = {
            "car_status": self.CAR_STATUS.get(status.get("car"), "unknown"),
            "charger_max_current": int(status.get("amp") or 0),
            "charger_absolute_max_current": int(status.get("ama") or 0),
            "charger_err": self.ERR.get(status.get("err"), "UNKNOWN"),
            "charger_access": self.ACCESS.get(status.get("acs"), "unknown"),
            "allow_charging": "on" if status.get("alw") is True else "off" if status.get("alw") is False else "unknown",
            "stop_mode": "unknown",
            "cable_lock_mode": int(status.get("ust") or 0),
            "cable_max_current": int(status.get("cbl") or 0),
            "pre_contactor_l1": "unknown",
            "pre_contactor_l2": "unknown",
            "pre_contactor_l3": "unknown",
            "post_contactor_l1": "unknown",
            "post_contactor_l2": "unknown",
            "post_contactor_l3": "unknown",
            "charger_temp": round(sum(float(item) for item in tma) / len(tma), 2) if tma else 0,
            "charger_temp0": round(float(value(tma, 0)), 2),
            "charger_temp1": round(float(value(tma, 1)), 2),
            "charger_temp2": round(float(value(tma, 2)), 2),
            "charger_temp3": round(float(value(tma, 3)), 2),
            "current_session_charged_energy": kwh(status.get("wh")),
            "charge_limit": kwh(status.get("dwo")),
            "adapter": "16A-Adapter" if status.get("adi") else "No Adapter",
            "unlocked_by_card": status.get("trx") or 0,
            "energy_total": kwh(status.get("eto")),
            "wifi": "connected" if status.get("wst") == 3 else "unknown" if status.get("wst") is None else "not connected",
            "u_l1": value(nrg, 0),
            "u_l2": value(nrg, 1),
            "u_l3": value(nrg, 2),
            "u_n": value(nrg, 3),
            "i_l1": value(nrg, 4),
            "i_l2": value(nrg, 5),
            "i_l3": value(nrg, 6),
            "p_l1": round(float(value(nrg, 7)) / 1000.0, 3),
            "p_l2": round(float(value(nrg, 8)) / 1000.0, 3),
            "p_l3": round(float(value(nrg, 9)) / 1000.0, 3),
            "p_n": round(float(value(nrg, 10)) / 1000.0, 3),
            "p_all": round(float(value(nrg, 11)) / 1000.0, 3),
            "lf_l1": value(nrg, 12),
            "lf_l2": value(nrg, 13),
            "lf_l3": value(nrg, 14),
            "lf_n": value(nrg, 15),
            "firmware": status.get("fwv", "unknown"),
            "serial_number": status.get("sse", "unknown"),
            "wifi_ssid": "unknown",
            "wifi_enabled": "unknown",
            "timezone_offset": int(status.get("tof") or 0),
            "timezone_dst_offset": int(status.get("tds") or 0),
            "force_state": status.get("frc"),
            "logic_mode": status.get("lmo"),
            "access_control": status.get("acs"),
            "phase_wish_mode": status.get("pwm"),
            "model_status": status.get("modelStatus"),
            "allowed_current": status.get("acu"),
            "force_single_phase": status.get("fsp"),
            "p_grid": status.get("pgrid"),
            "p_pv": status.get("ppv"),
            "p_akku": status.get("pakku"),
            "pv_surplus": "on" if status.get("fup") else "off" if "fup" in status else None,
            "awattar": "on" if status.get("awe") else "off" if "awe" in status else None,
            "zero_feed_in": "on" if status.get("fzf") else "off" if "fzf" in status else None,
            "simulate_unplugging_short": "on" if status.get("su") else "off" if "su" in status else None,
            "simulate_unplugging_always": "on" if status.get("sua") else "off" if "sua" in status else None,
        }
        for key, info in V2_NUMBERS.items():
            if key in status:
                data[info.get("attribute", info["name"].lower().replace(" ", "_").replace("-", "_"))] = kwh(status[key]) if key == "dwo" else status[key]
        return data

    def setTmpMaxCurrent(self, current):
        return self._set("amp", self._clamp_current(current))

    def setAbsoluteMaxCurrent(self, current):
        return self._set("ama", self._clamp_current(current))

    def setCableLockMode(self, mode):
        return self._set("ust", max(0, min(int(mode), 2)))

    def setChargeLimit(self, chargeLimit):
        chargeLimit = float(chargeLimit)
        return self._set("dwo", None if chargeLimit <= 0 else int(chargeLimit * 1000))

    def setAllowCharging(self, allow):
        return self._set("frc", 2 if allow else 1)

    def setApiKey(self, key, value):
        return self._set(key, value)


def create_charger(host, api_version=DEFAULT_API_VERSION):
    api_version = api_version or DEFAULT_API_VERSION
    if api_version == API_VERSION_V1:
        return GoeChargerV1(host)
    if api_version == API_VERSION_V2:
        return GoeChargerV2(host)
    raise ValueError(f"Unsupported go-eCharger API version: {api_version}")
