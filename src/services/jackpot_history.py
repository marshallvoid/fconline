from datetime import datetime
from typing import Dict, List, Optional, TypedDict

from src.utils.contants import DUPLICATE_WINDOW_SECONDS


class HistoryEntry(TypedDict):
    timestamp: str
    value: str


class EventTimeline(TypedDict):
    start_time: str
    end_time: str
    type: str
    value: str
    history: List[HistoryEntry]


class JackpotHistoryManager:
    _instance: Optional["JackpotHistoryManager"] = None
    _events_dict: Dict[str, List[EventTimeline]] = {}

    @classmethod
    def instance(cls, event_name: str) -> "JackpotHistoryManager":
        if not cls._instance:
            cls._instance = cls()

        if event_name not in cls._events_dict:
            cls._events_dict[event_name] = []
            cls.new_timeline(event_name=event_name)

        return cls._instance

    @classmethod
    def new_timeline(cls, event_name: str) -> EventTimeline:
        cls._events_dict[event_name].append(
            {
                "start_time": datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
                "end_time": datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
                "type": "Unknown",
                "value": "0",
                "history": [],
            }
        )

        return cls._events_dict[event_name][-1]

    def update_history_entry(self, event_name: str, timestamp: str, value: str) -> None:
        timelines = self._events_dict[event_name]
        latest_start_time = self._get_latest_start_time(event_name=event_name)

        event_timeline = next((timeline for timeline in timelines if timeline["start_time"] == latest_start_time), None)
        if not event_timeline:
            event_timeline = self.new_timeline(event_name=event_name)

        is_duplicate = False
        new_dt = datetime.strptime(timestamp, "%d-%m-%Y %H:%M:%S")
        for entry in reversed(event_timeline["history"]):
            if str(entry["value"]) != str(value):
                continue

            try:
                old_ts = str(entry["timestamp"])
                old_dt = datetime.strptime(old_ts, "%d-%m-%Y %H:%M:%S")

            except Exception:
                # If cannot parse, treat as non-duplicate and continue search
                continue

            # If the prior identical value is within the window, skip as duplicate
            if abs((new_dt - old_dt).total_seconds()) <= DUPLICATE_WINDOW_SECONDS:
                is_duplicate = True

            break

        # Only append if not duplicate in the time window
        if not is_duplicate:
            event_timeline["history"].append({"timestamp": timestamp, "value": value})

    def update_timeline(self, event_name: str, type: str, value: str) -> None:
        timelines = self._events_dict[event_name]
        latest_start_time = self._get_latest_start_time(event_name=event_name)

        event_timeline = next((timeline for timeline in timelines if timeline["start_time"] == latest_start_time), None)
        if not event_timeline:
            event_timeline = self.new_timeline(event_name=event_name)

        event_timeline["end_time"] = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        event_timeline["type"] = type
        event_timeline["value"] = value

    def _get_latest_start_time(self, event_name: str) -> str:
        timelines = self._events_dict[event_name]
        latest_start_time = max(event["start_time"] for event in timelines)
        return latest_start_time
