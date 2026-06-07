"""
AI Engine - Claude API Integration
===================================
Handles all communication with Claude Haiku 4.5 via the Anthropic SDK.
Uses streaming for fast perceived response time.
"""

import anthropic
from typing import Generator


class AIEngine:
    """Claude API wrapper with streaming support for real-time meeting assistance."""

    def __init__(self):
        from config import (
            CLAUDE_API_KEY, CLAUDE_MODEL, CLAUDE_MAX_TOKENS,
            CLAUDE_TEMPERATURE, CLAUDE_SYSTEM_PROMPT, USER_CONTEXT,
            CONTEXT_MAX_CHARS
        )
        if not CLAUDE_API_KEY:
            raise ValueError(
                "CLAUDE_API_KEY not set! "
                "Set ANTHROPIC_API_KEY environment variable or edit config.py"
            )

        self.client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)
        self.model = CLAUDE_MODEL
        self.max_tokens = CLAUDE_MAX_TOKENS
        self.temperature = CLAUDE_TEMPERATURE
        self.context_max_chars = CONTEXT_MAX_CHARS

        # Stitch the user-situation block onto the system prompt so Sonnet
        # tailors every answer to the user's role, stack, and meeting context.
        self.system_prompt = (
            f"{CLAUDE_SYSTEM_PROMPT}\n\n"
            f"ABOUT THE USER:\n{USER_CONTEXT}"
        )

        # Multi-turn memory: every End press appends a (user, assistant) pair.
        # Reset by calling reset_conversation() when the user starts a new session.
        self.conversation_history: list = []

    def reset_conversation(self):
        """Wipe multi-turn memory. Called when the user presses HOME (reset session)."""
        self.conversation_history = []

    def answer_screenshot(self, image_b64: str) -> Generator[str, None, None]:
        """
        Single-screenshot mode (current production flow).
        The user pressed INSERT — capture their screen, ask Sonnet for the answer,
        stream it back. Conversation memory is preserved across calls so the user
        can take follow-up screenshots in the same session.

        Args:
            image_b64: Base64-encoded PNG screenshot.

        Yields:
            Text chunks as Sonnet streams the answer.
        """
        # Build a minimal multimodal user message: a tiny label, the image,
        # and a tight instruction. The strict format rules live in the system
        # prompt (cached), so we don't need to repeat them here.
        user_content = [
            {"type": "text", "text": "[SCREENSHOT OF THE INTERVIEW QUESTION]"},
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": image_b64,
                },
            },
            {"type": "text", "text": "Answer the question in the screenshot. Code block first, then 1-2 sentences. No preambles."},
        ]

        # Append to running history BEFORE the API call. If the stream errors,
        # this turn is still saved so the user can see what was asked.
        self.conversation_history.append({"role": "user", "content": user_content})

        # Cache the system prompt — identical across every screenshot in a session,
        # so Anthropic prompt caching drops repeat input cost dramatically.
        cached_system = [{
            "type": "text",
            "text": self.system_prompt,
            "cache_control": {"type": "ephemeral"},
        }]

        full_response_parts = []
        with self.client.messages.stream(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            system=cached_system,
            messages=self.conversation_history,
        ) as stream:
            for text_chunk in stream.text_stream:
                full_response_parts.append(text_chunk)
                yield text_chunk

        # Save Sonnet's full reply so the NEXT screenshot in this session
        # has context of what was previously asked and answered.
        self.conversation_history.append({
            "role": "assistant",
            "content": "".join(full_response_parts),
        })

    def get_response_with_context(
        self,
        transcript: str,
        screenshots: list,
    ) -> Generator[str, None, None]:
        """
        THE GOD BUTTON. Answers using:
        - Recent audio transcript
        - All queued screenshots (zero or more)
        - Full prior conversation history in this session

        Streams Sonnet's response and saves it back into history so the next
        End press has memory of this exchange.

        Args:
            transcript: Recent audio transcript text (string).
            screenshots: List of base64-encoded PNG images (may be empty).

        Yields:
            Text chunks as Sonnet streams them.
        """
        # Build the multimodal user message as a list of content blocks.
        # We label each image with "[SCREENSHOT N of M]" before it so the
        # model can bind the image to its order/role in the question.
        content_blocks = []

        transcript_text = transcript[-self.context_max_chars:] if transcript else "(No audio captured yet.)"
        content_blocks.append({
            "type": "text",
            "text": f"[AUDIO TRANSCRIPT — what's been said in the meeting]\n{transcript_text}",
        })

        if screenshots:
            total = len(screenshots)
            for index, image_b64 in enumerate(screenshots, start=1):
                content_blocks.append({
                    "type": "text",
                    "text": f"[SCREENSHOT {index} of {total}]",
                })
                content_blocks.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": image_b64,
                    },
                })

        content_blocks.append({
            "type": "text",
            "text": "Based on the transcript and screenshots above, answer or assist. Lead with the direct answer.",
        })

        # Append this turn to the running history BEFORE the API call so that
        # if the stream errors, the user can press End again and retry cleanly
        # by replacing the trailing user turn (we don't auto-retry here yet).
        self.conversation_history.append({"role": "user", "content": content_blocks})

        # Cache the system prompt — it's identical across every End press in
        # a session, so Anthropic prompt caching cuts repeat input cost ~90%.
        cached_system = [{
            "type": "text",
            "text": self.system_prompt,
            "cache_control": {"type": "ephemeral"},
        }]

        full_response_parts = []
        with self.client.messages.stream(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            system=cached_system,
            messages=self.conversation_history,
        ) as stream:
            for text_chunk in stream.text_stream:
                full_response_parts.append(text_chunk)
                yield text_chunk

        # Save Sonnet's full response back into history so the NEXT End press
        # remembers what was just answered.
        self.conversation_history.append({
            "role": "assistant",
            "content": "".join(full_response_parts),
        })

    def get_response_stream(self, transcript: str, context: str = "") -> Generator[str, None, None]:
        """
        Get a streaming response from Claude based on meeting transcript.

        Args:
            transcript: The latest transcript chunk
            context: Previous transcript context (for continuity)

        Yields:
            Text chunks as they arrive from Claude
        """
        # Build the message with context
        user_content = ""
        if context:
            user_content += f"[Previous conversation context]\n{context[-self.context_max_chars:]}\n\n"
        user_content += f"[Latest transcript]\n{transcript}\n\n"
        user_content += "Provide a helpful, concise response or suggestion based on what's being discussed."

        with self.client.messages.stream(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            system=self.system_prompt,
            messages=[{"role": "user", "content": user_content}]
        ) as stream:
            for text in stream.text_stream:
                yield text

    def get_response(self, transcript: str, context: str = "") -> str:
        """
        Get a complete (non-streaming) response from Claude.

        Args:
            transcript: The latest transcript chunk
            context: Previous transcript context

        Returns:
            Complete response string
        """
        parts = []
        for chunk in self.get_response_stream(transcript, context):
            parts.append(chunk)
        return "".join(parts)

    def get_response_with_screenshot(self, transcript: str, screenshot_b64: str, context: str = "") -> Generator[str, None, None]:
        """
        Get a streaming response using both transcript and screenshot.
        Uses Claude's vision capability.

        Args:
            transcript: Recent transcript text
            screenshot_b64: Base64-encoded screenshot image
            context: Previous transcript context

        Yields:
            Text chunks as they arrive
        """
        user_content = []

        # Add text context
        text_part = ""
        if context:
            text_part += f"[Previous context]\n{context[-self.context_max_chars:]}\n\n"
        text_part += f"[Latest transcript]\n{transcript}\n\n"
        text_part += "[Screenshot of current screen is attached]\n"
        text_part += "Analyze both the conversation and what's on screen. Provide relevant assistance."

        user_content.append({"type": "text", "text": text_part})
        user_content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/png",
                "data": screenshot_b64,
            }
        })

        with self.client.messages.stream(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            system=self.system_prompt,
            messages=[{"role": "user", "content": user_content}]
        ) as stream:
            for text in stream.text_stream:
                yield text

    def generate_summary(self, full_transcript: str) -> str:
        """
        Generate a meeting summary with key points and action items.

        Args:
            full_transcript: The complete meeting transcript

        Returns:
            Formatted summary string
        """
        prompt = f"""Here is the complete transcript of a meeting:

{full_transcript}

Please generate:
1. **Meeting Summary** (3-5 bullet points)
2. **Key Decisions** (if any)
3. **Action Items** (with owners if mentioned)
4. **Follow-up Topics** (things that need further discussion)

Format it clearly in markdown."""

        response = self.client.messages.create(
            model=self.model,
            max_tokens=2048,
            temperature=0.2,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text

    def answer_question(self, question: str, transcript_context: str) -> Generator[str, None, None]:
        """
        Directly answer a specific question using meeting context.

        Args:
            question: The question to answer
            transcript_context: Relevant transcript for context

        Yields:
            Streaming response chunks
        """
        prompt = f"""Meeting context:
{transcript_context[-self.context_max_chars:]}

Question being asked: {question}

Provide a clear, direct answer. Be concise."""

        with self.client.messages.stream(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            system=self.system_prompt,
            messages=[{"role": "user", "content": prompt}]
        ) as stream:
            for text in stream.text_stream:
                yield text
