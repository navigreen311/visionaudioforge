"""Call intelligence: summarization, action items, sentiment, talk ratio."""

from __future__ import annotations

import re
from typing import Any

import numpy as np

from app.services.audio.diarization import SpeakerDiarizer
from app.services.audio.stt import SpeechToTextService


# Sentiment word lists
_POSITIVE_WORDS = {
    "good", "great", "excellent", "agree", "happy", "wonderful", "fantastic",
    "perfect", "amazing", "love", "like", "best", "better", "pleased",
    "appreciate", "thank", "thanks", "positive", "success", "successful",
    "well", "nice", "awesome", "brilliant", "outstanding",
}

_NEGATIVE_WORDS = {
    "bad", "wrong", "problem", "issue", "disagree", "concerned", "worry",
    "terrible", "horrible", "awful", "poor", "fail", "failure", "hate",
    "dislike", "worst", "worse", "disappointed", "unfortunately", "difficult",
    "trouble", "risk", "error", "mistake", "frustrat",
}

# Action verb patterns
_ACTION_PATTERNS = [
    r"\bwill\b", r"\bshould\b", r"\bneed to\b", r"\bmust\b",
    r"\baction item\b", r"\bfollow up\b", r"\btake care of\b",
    r"\bgoing to\b", r"\bhave to\b", r"\blet'?s\b",
]

# Key phrase patterns for meeting summaries
_KEY_PHRASES = [
    r"\bdecided\b", r"\bagreed\b", r"\bwill do\b", r"\baction item\b",
    r"\bnext steps?\b", r"\bdeadline\b", r"\bconcluded\b", r"\bsummar",
    r"\bkey point\b", r"\bimportant\b", r"\bpriority\b",
]

_DECISION_PHRASES = [
    r"\bdecided\b", r"\bagreed\b", r"\bconcluded\b", r"\bapproved\b",
    r"\bconfirmed\b", r"\bresolved\b",
]

# Date/time patterns for deadline extraction
_DATE_PATTERNS = [
    r"\b\d{1,2}/\d{1,2}/\d{2,4}\b",
    r"\b\d{4}-\d{2}-\d{2}\b",
    r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\s+\d{1,2}(?:\s*,?\s*\d{4})?\b",
    r"\b(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
    r"\b(?:today|tomorrow|next week|end of (?:day|week|month))\b",
    r"\bby\s+\w+day\b",
]


class CallIntelligence:
    """Analyze calls/meetings: transcription, diarization, summary, sentiment."""

    def __init__(self) -> None:
        self._stt = SpeechToTextService()
        self._diarizer = SpeakerDiarizer()

    async def analyze_call(
        self,
        audio: np.ndarray,
        sr: int,
    ) -> dict:
        """Full call analysis pipeline.

        Returns CallAnalysis with transcript, speakers, summary,
        action_items, sentiment, duration_s, talk_ratio.
        """
        duration_s = len(audio) / sr

        # Step 1: Transcribe
        transcription = await self._stt.transcribe(audio, sr)

        # Step 2: Diarize
        diarization = self._diarizer.diarize(audio, sr)

        # Step 3: Get speaker transcript
        speaker_transcript = self._diarizer.get_speaker_transcript(
            diarization, transcription
        )

        # Step 4: Summarize
        summary_result = self.summarize_meeting(speaker_transcript)

        # Step 5: Extract action items
        action_items = self.extract_action_items(speaker_transcript)

        # Step 6: Sentiment analysis
        sentiment = self.analyze_sentiment_per_speaker(speaker_transcript)

        # Step 7: Talk ratio
        talk_ratio = self.compute_talk_ratio(diarization)

        return {
            "transcript": transcription.get("text", ""),
            "speakers": diarization.get("segments", []),
            "summary": summary_result.get("summary", ""),
            "action_items": [item["action"] for item in action_items],
            "sentiment": sentiment,
            "duration_s": round(duration_s, 3),
            "talk_ratio": talk_ratio,
        }

    def summarize_meeting(
        self,
        transcript_segments: list[dict],
    ) -> dict:
        """Extract summary, key points, and decisions from transcript segments.

        V1: finds sentences with key phrases and groups them.

        Args:
            transcript_segments: List of dicts with 'speaker', 'text',
                                 'start_s', 'end_s'.

        Returns:
            Dict with summary, key_points, decisions.
        """
        if not transcript_segments:
            return {"summary": "", "key_points": [], "decisions": []}

        all_text = " ".join(seg.get("text", "") for seg in transcript_segments)
        sentences = _split_sentences(all_text)

        key_points: list[str] = []
        decisions: list[str] = []

        for sentence in sentences:
            sentence_lower = sentence.lower()

            # Check for decision phrases
            is_decision = any(
                re.search(pat, sentence_lower) for pat in _DECISION_PHRASES
            )
            if is_decision:
                decisions.append(sentence.strip())
                continue

            # Check for key phrases
            is_key = any(
                re.search(pat, sentence_lower) for pat in _KEY_PHRASES
            )
            if is_key:
                key_points.append(sentence.strip())

        # Build summary from speakers and key content
        speakers = set(seg.get("speaker", "") for seg in transcript_segments)
        n_speakers = len(speakers)

        summary_parts = []
        if n_speakers > 0:
            summary_parts.append(
                f"Meeting with {n_speakers} participant(s)."
            )
        if key_points:
            summary_parts.append(
                f"{len(key_points)} key point(s) discussed."
            )
        if decisions:
            summary_parts.append(
                f"{len(decisions)} decision(s) made."
            )
        if not summary_parts:
            # Fallback: use first few words of transcript
            preview = all_text[:200].strip()
            if preview:
                summary_parts.append(preview)

        return {
            "summary": " ".join(summary_parts),
            "key_points": key_points,
            "decisions": decisions,
        }

    def extract_action_items(
        self,
        transcript_segments: list[dict],
    ) -> list[dict]:
        """Extract action items from transcript segments.

        V1: finds sentences with action verbs. Assignee = speaker name.
        Deadline = any date/time pattern found in the sentence.

        Returns:
            List of dicts with action, assignee, deadline, speaker.
        """
        if not transcript_segments:
            return []

        action_items: list[dict] = []

        for seg in transcript_segments:
            speaker = seg.get("speaker", None)
            text = seg.get("text", "")
            sentences = _split_sentences(text)

            for sentence in sentences:
                sentence_lower = sentence.lower()

                # Check for action patterns
                has_action = any(
                    re.search(pat, sentence_lower) for pat in _ACTION_PATTERNS
                )
                if not has_action:
                    continue

                # Extract deadline if present
                deadline = None
                for date_pat in _DATE_PATTERNS:
                    match = re.search(date_pat, sentence_lower)
                    if match:
                        deadline = match.group(0)
                        break

                action_items.append(
                    {
                        "action": sentence.strip(),
                        "assignee": speaker,
                        "deadline": deadline,
                        "speaker": speaker,
                    }
                )

        return action_items

    def analyze_sentiment_per_speaker(
        self,
        transcript_segments: list[dict],
    ) -> dict[str, dict]:
        """Analyze sentiment per speaker using keyword-based approach.

        V1: simple positive/negative word counting.

        Returns:
            Dict mapping speaker name to sentiment dict with overall and scores.
        """
        if not transcript_segments:
            return {}

        # Group text by speaker
        speaker_texts: dict[str, list[str]] = {}
        for seg in transcript_segments:
            speaker = seg.get("speaker", "Unknown")
            text = seg.get("text", "")
            speaker_texts.setdefault(speaker, []).append(text)

        result: dict[str, dict] = {}

        for speaker, texts in speaker_texts.items():
            all_words = " ".join(texts).lower().split()
            total_words = len(all_words) if all_words else 1

            positive_count = sum(1 for w in all_words if w.strip(".,!?;:") in _POSITIVE_WORDS)
            negative_count = sum(1 for w in all_words if w.strip(".,!?;:") in _NEGATIVE_WORDS)
            neutral_count = total_words - positive_count - negative_count

            pos_score = round(positive_count / total_words, 4)
            neg_score = round(negative_count / total_words, 4)
            neu_score = round(neutral_count / total_words, 4)

            # Determine overall sentiment
            if pos_score > neg_score:
                overall = "positive"
            elif neg_score > pos_score:
                overall = "negative"
            else:
                overall = "neutral"

            result[speaker] = {
                "overall": overall,
                "scores": {
                    "positive": pos_score,
                    "negative": neg_score,
                    "neutral": neu_score,
                },
            }

        return result

    def compute_talk_ratio(
        self,
        diarization: dict,
    ) -> dict[str, dict]:
        """Compute talk time ratio per speaker.

        Args:
            diarization: Result from SpeakerDiarizer.diarize().

        Returns:
            Dict mapping speaker name to time_s, percentage, interruptions.
        """
        segments = diarization.get("segments", [])
        if not segments:
            return {}

        # Accumulate per-speaker talk time
        speaker_time: dict[str, float] = {}
        speaker_interruptions: dict[str, int] = {}

        for seg in segments:
            speaker = seg["speaker"]
            duration = seg.get("duration_s", seg["end_s"] - seg["start_s"])
            speaker_time[speaker] = speaker_time.get(speaker, 0.0) + duration
            speaker_interruptions.setdefault(speaker, 0)

        # Count interruptions: when a speaker's segment follows a different
        # speaker's segment and starts very close to or overlapping the end
        for i in range(1, len(segments)):
            curr = segments[i]
            prev = segments[i - 1]
            if curr["speaker"] != prev["speaker"]:
                # If current segment starts before previous ends, it's an interruption
                gap = curr["start_s"] - prev["end_s"]
                if gap < 0.5:  # less than 0.5s gap counts as interruption
                    speaker_interruptions[curr["speaker"]] = (
                        speaker_interruptions.get(curr["speaker"], 0) + 1
                    )

        total_time = sum(speaker_time.values())
        if total_time == 0:
            total_time = 1.0

        result: dict[str, dict] = {}
        for speaker in sorted(speaker_time.keys()):
            time_s = speaker_time[speaker]
            result[speaker] = {
                "time_s": round(time_s, 3),
                "percentage": round(time_s / total_time * 100.0, 2),
                "interruptions": speaker_interruptions.get(speaker, 0),
            }

        return result


def _split_sentences(text: str) -> list[str]:
    """Split text into sentences using basic punctuation rules."""
    # Split on sentence-ending punctuation followed by space or end
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    return [s for s in sentences if s.strip()]
