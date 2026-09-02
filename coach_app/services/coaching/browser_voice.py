"""Low-latency browser voice output using Web Speech API."""

from __future__ import annotations

import json
import streamlit as st
import streamlit.components.v1 as components


LANGUAGE_CODES = {
    "English": "en-US",
    "Telugu": "te-IN",
    "Hindi": "hi-IN",
}


def render_voice_controller(auto_start=False):
    components.html(
        """
        <div style="width:100%;box-sizing:border-box;padding:10px 4px;font-family:Arial,sans-serif;">
          <div style="border:2px solid #22c55e;border-radius:12px;padding:12px;background:#0b1220;color:white;">
            <div style="font-size:14px;font-weight:700;margin-bottom:8px;">🎙️ LIVE AI TRAINER VOICE</div>
            <button id="auto" style="
              width:100%;min-height:42px;border:0;border-radius:9px;
              background:#12351f;color:#86efac;font-size:15px;font-weight:800;cursor:pointer;
            ">🎙️ ENABLE COACH VOICE</button>
            <div id="status" style="margin-top:7px;font-size:12px;color:#d1d5db;">
              Tap once to allow the trainer to speak.
            </div>
          </div>
        </div>

        <script>
        (() => {
          const host = window.parent || window;
          const synth = host.speechSynthesis;
          const state = host.__AI_GYM_VOICE__ || {
            unlocked:false, speaking:false, queue:[], lastId:0, voices:[]
          };
          host.__AI_GYM_VOICE__ = state;

          const btn = document.getElementById("auto");
          const status = document.getElementById("status");

          if (!synth) {
            status.textContent = "Speech synthesis is unavailable in this browser.";
            btn.disabled = true;
            return;
          }

          const loadVoices = () => { state.voices = synth.getVoices(); };
          loadVoices();
          if ("onvoiceschanged" in synth) synth.onvoiceschanged = loadVoices;

          function unlock(speakTest=false) {
            state.unlocked = true;
            state.voices = synth.getVoices();

            if (speakTest) {
              synth.cancel();
              const u = new SpeechSynthesisUtterance("Coach voice is ready. Let's train.");
              u.lang = "en-US";
              u.rate = 1.0;
              u.volume = 1.0;
              state.speaking = true;
              u.onend = u.onerror = () => { state.speaking = false; };
              try { synth.speak(u); } catch(e) { state.speaking = false; }
            }

            status.textContent = "✅ Coach voice is active.";
            status.style.color = "#4ade80";
            btn.textContent = "🎙️ COACH VOICE ACTIVE";
          }

          btn.addEventListener("click", () => unlock(true));

          try {
            window.parent.document.addEventListener(
              "pointerdown", () => unlock(false), {once:true, capture:true}
            );
          } catch(e) {}

          window.addEventListener(
            "pointerdown", () => unlock(false), {once:true, capture:true}
          );

          const AUTO_START = __AUTO_START__;
          if (AUTO_START) setTimeout(() => unlock(false), 50);
        })();
        </script>
        """.replace("__AUTO_START__", "true" if auto_start else "false"),
        height=125,
        scrolling=False,
    )


def render_browser_voice(
    text: str,
    language="English",
    event_id=0,
    rate=1.02,
    volume=1.0,
    priority="normal",
):
    text = (text or "").strip()
    if not text:
        return

    lang = json.dumps(LANGUAGE_CODES.get(language, "en-US"))
    payload = json.dumps(text, ensure_ascii=False)
    eid = int(event_id)
    rate = max(0.78, min(1.30, float(rate)))
    volume = max(0.0, min(1.0, float(volume)))
    priority = json.dumps(priority)

    components.html(
        f"""
        <script>
        (() => {{
          const host = window.parent || window;
          const s = host.speechSynthesis || window.speechSynthesis;
          const state = host.__AI_GYM_VOICE__ || (host.__AI_GYM_VOICE__ = {{
            unlocked:false, speaking:false, queue:[], lastId:0, voices:[]
          }});

          const id = {eid};
          if (!s || !state.unlocked || id <= state.lastId) return;
          state.lastId = id;

          const item = {{
            text:{payload},
            lang:{lang},
            rate:{rate},
            volume:{volume},
            priority:{priority}
          }};

          if (item.priority === "high") {{
            state.queue = state.queue.filter(x => x.priority === "high");
            if (s.speaking) s.cancel();
            state.speaking = false;
          }}

          state.queue.push(item);
          if (state.queue.length > 3) state.queue = state.queue.slice(-3);

          function next() {{
            if (state.speaking || !state.queue.length) return;

            const x = state.queue.shift();
            state.speaking = true;

            const u = new SpeechSynthesisUtterance(x.text);
            u.lang = x.lang;
            u.rate = x.rate;
            u.volume = x.volume;
            u.pitch = 1;

            const voices = s.getVoices();
            const prefix = x.lang.slice(0,2).toLowerCase();
            const v = voices.find(v => v.lang && v.lang.toLowerCase().startsWith(prefix));
            if (v) u.voice = v;

            u.onend = u.onerror = () => {{
              state.speaking = false;
              setTimeout(next, 40);
            }};

            try {{ s.speak(u); }}
            catch(e) {{ state.speaking = false; setTimeout(next, 40); }}
          }}

          next();
        }})();
        </script>
        """,
        height=1,
        scrolling=False,
    )


def render_voice_status(enabled: bool, language: str):
    st.caption(f"🔊 Voice Coach: **{'ON' if enabled else 'OFF'}** · {language}")
