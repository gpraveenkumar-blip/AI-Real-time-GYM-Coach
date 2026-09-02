"""Real-time deterministic voice director for the gym coach.

Camera/pose events are handled locally so tracking never waits for an LLM.
The LLM is optional and reserved for higher-level conversational feedback.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field


LANG = {
    "English": {
        "start": "Let's work. Eyes forward, core tight, and breathe. I'll count every rep.",
        "rep": ["Good rep.", "Strong.", "Keep that rhythm.", "Nice control.", "That's it."],
        "half": "You're halfway there. Stay strong.",
        "last": "Last few. Finish clean.",
        "set": "Set complete. Breathe, shake it out, and get ready for the next set.",
        "complete": "Workout complete. Excellent work. Recover, hydrate, and come back stronger.",
        "no_pose": "I can't see you clearly. Step back into the frame so I can coach you.",
        "form": "Fix your form before the next rep.",
        "breathe": "Breathe out through the effort.",
        "rest": "Take a short recovery. Control your breathing.",
    },
    "Hindi": {
        "start": "चलो शुरू करते हैं। फॉर्म मजबूत रखो, सांस नियंत्रित रखो। मैं हर रेप गिनूंगा।",
        "rep": ["अच्छा रेप।", "बहुत बढ़िया।", "रिदम बनाए रखो।", "कंट्रोल अच्छा है।", "ऐसे ही।"],
        "half": "आधा हो गया। मजबूत बने रहो।",
        "last": "आखिरी कुछ रेप। साफ फॉर्म के साथ खत्म करो।",
        "set": "सेट पूरा। सांस संभालो और अगले सेट के लिए तैयार हो जाओ।",
        "complete": "वर्कआउट पूरा। शानदार काम। आराम करो, पानी पियो और फिर मजबूत होकर लौटो।",
        "no_pose": "मैं आपको साफ नहीं देख पा रहा। फ्रेम में सही जगह आओ।",
        "form": "अगले रेप से पहले अपना फॉर्म ठीक करो।",
        "breathe": "मेहनत करते समय सांस बाहर छोड़ो।",
        "rest": "थोड़ा आराम करो और सांस नियंत्रित करो।",
    },
    "Telugu": {
        "start": "మొదలుపెడదాం. ఫారమ్ బలంగా ఉంచండి, శ్వాసను నియంత్రించండి. నేను ప్రతి రెప్‌ను లెక్కిస్తాను.",
        "rep": ["చాలా బాగుంది.", "బలంగా ఉంది.", "రిథమ్ కొనసాగించండి.", "కంట్రోల్ చాలా బాగుంది.", "అలాగే కొనసాగించండి."],
        "half": "సగం పూర్తైంది. బలంగా కొనసాగించండి.",
        "last": "ఇంకా చివరి కొన్ని రెప్స్. మంచి ఫారమ్‌తో పూర్తి చేయండి.",
        "set": "సెట్ పూర్తైంది. శ్వాస తీసుకుని తర్వాతి సెట్‌కు సిద్ధం అవ్వండి.",
        "complete": "వర్కౌట్ పూర్తైంది. అద్భుతంగా చేశారు. విశ్రాంతి తీసుకుని నీరు తాగండి.",
        "no_pose": "మీరు స్పష్టంగా కనిపించడం లేదు. ఫ్రేమ్‌లోకి సరైన స్థితిలో రండి.",
        "form": "తర్వాతి రెప్‌కు ముందు మీ ఫారమ్‌ను సరిచేయండి.",
        "breathe": "శ్రమ చేసే సమయంలో శ్వాసను బయటకు వదలండి.",
        "rest": "కొద్దిసేపు విశ్రాంతి తీసుకుని శ్వాసను నియంత్రించండి.",
    },
}


@dataclass
class LiveVoiceDirector:
    llm: object | None = None
    enabled: bool = True
    min_form_interval: float = 3.5
    min_no_pose_interval: float = 5.0
    min_breath_interval: float = 12.0
    last_reps: int = 0
    last_sets: int = 0
    last_form_issue: str = ""
    last_form_at: float = 0.0
    last_no_pose_at: float = 0.0
    last_breath_at: float = 0.0
    last_event_at: float = 0.0
    event_id: int = 0
    _phrase_index: int = 0
    _milestones: set = field(default_factory=set)

    def reset(self):
        self.last_reps = 0
        self.last_sets = 0
        self.last_form_issue = ""
        self.last_form_at = 0
        self.last_no_pose_at = 0
        self.last_breath_at = 0
        self.last_event_at = 0
        self.event_id = 0
        self._phrase_index = 0
        self._milestones = set()

    def _event(self, text, kind="coach", priority="normal"):
        if not self.enabled or not text:
            return None
        self.event_id += 1
        self.last_event_at = time.monotonic()
        return {
            "id": self.event_id,
            "text": text.strip(),
            "kind": kind,
            "priority": priority,
        }

    def llm_feedback(self, event, language, context=None, issue=None):
        if not self.llm:
            return None
        try:
            return self.llm.give_feedback(
                event=event,
                issue=issue,
                language=language,
                context=context,
            )
        except Exception as e:
            print(f"LLM coach error: {e}")
            return None

    def start(self, exercise, language):
        self.reset()
        return self._event(
            LANG.get(language, LANG["English"])["start"],
            "start",
            "high",
        )

    def on_metrics(
        self,
        exercise,
        metrics,
        total_reps,
        sets_completed,
        target_sets,
        pose_detected,
        language,
    ):
        if not self.enabled:
            return []

        now = time.monotonic()
        local = LANG.get(language, LANG["English"])
        events = []

        reps = int(total_reps or 0)
        sets = int(sets_completed or 0)
        target = int(target_sets or 0)

        if reps > self.last_reps:
            for rep in range(self.last_reps + 1, reps + 1):
                phrase = local["rep"][self._phrase_index % len(local["rep"])]
                self._phrase_index += 1

                event = self._event(f"{rep}. {phrase}", "rep", "normal")
                if event:
                    events.append(event)

                if target > 0 and rep == max(1, target // 2) and "half" not in self._milestones:
                    self._milestones.add("half")
                    event = self._event(local["half"], "motivation")
                    if event:
                        events.append(event)

                if target > 2 and rep == target - 2 and "last" not in self._milestones:
                    self._milestones.add("last")
                    event = self._event(local["last"], "motivation", "high")
                    if event:
                        events.append(event)

            self.last_reps = reps

        if sets > self.last_sets:
            for n in range(self.last_sets + 1, sets + 1):
                event = self._event(
                    f"{local['set']} Set {n} of {target}.",
                    "set",
                    "high",
                )
                if event:
                    events.append(event)
            self.last_sets = sets

        if not pose_detected and now - self.last_no_pose_at >= self.min_no_pose_interval:
            self.last_no_pose_at = now
            event = self._event(local["no_pose"], "pose", "high")
            if event:
                events.append(event)

        metrics = metrics or {}
        issue = str(metrics.get("issue") or metrics.get("form_issue") or "")
        status = str(metrics.get("form_status") or "")
        bad = status and status.upper() not in {
            "GOOD FORM", "GOOD LINE", "TRACKING", "N/A", "READY", ""
        }

        if issue or bad:
            cue = issue or status
            if cue != self.last_form_issue or now - self.last_form_at >= self.min_form_interval:
                self.last_form_issue = cue
                self.last_form_at = now
                event = self._event(
                    f"{local['form']} {cue}.",
                    "form",
                    "high",
                )
                if event:
                    events.append(event)

        if pose_detected and now - self.last_breath_at >= self.min_breath_interval and reps > 0:
            self.last_breath_at = now
            event = self._event(local["breathe"], "breath")
            if event:
                events.append(event)

        return events[-4:]

    def finish(self, exercise, language):
        return self._event(
            LANG.get(language, LANG["English"])["complete"],
            "complete",
            "high",
        )
