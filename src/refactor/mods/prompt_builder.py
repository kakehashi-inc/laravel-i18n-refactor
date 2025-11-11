"""Prompt builder for AI translation."""

import re
import html
from typing import List, Dict, Tuple, Optional


class PromptBuilder:
    """AI翻訳用のプロンプト構築"""

    def __init__(self, summary: Optional[str] = None):
        """
        Initialize PromptBuilder.

        Args:
            summary: Application summary for context-aware translation
        """
        self.summary = summary

    def build_prompt(self, items: List[Dict], languages: List[Tuple[str, str]]) -> str:
        """
        Build translation prompt for AI using improved XML format.

        Args:
            items: List of items to translate
            languages: List of target languages

        Returns:
            Formatted prompt string
        """
        # Build language tags list
        lang_tags = " and ".join([f"<{code}>" for code, _ in languages])
        lang_descriptions = "\n".join([f"   - <{code}>: {desc}" for code, desc in languages])

        # Start prompt with role definition
        prompt = "You are a professional translator for Laravel web applications.\n\n"

        # Add application summary if provided - critical for context
        if self.summary:
            prompt += f"""# Application Context
{self.summary}

Consider this context when:
- Choosing terminology (use domain-specific vocabulary)
- Interpreting ambiguous strings (e.g., "post" could be blog post, mail post, or HTTP POST)
- Determining translation necessity (technical vs user-facing)
- Maintaining consistency with application domain

"""

        prompt += f"""# Task
Translate extracted strings for internationalization (i18n).

For each <request>:
1. Examine <reference> to understand the code context (HTML structure, attributes, surrounding code)
2. Determine if the text is user-facing or technical
3. If user-facing: provide natural translations in {lang_tags} tags
4. If technical (CSS class, data attribute, code identifier, dimension, etc.): return <translations>false</translations>

# Guidelines
- User-facing: button labels, messages, titles, descriptions, error messages
- Technical: class names (btn-primary, nav-item), IDs, data-* attributes, dimensions (1920x1080), hex colors (#fff)
- Consider HTML structure: text in <p>, <h1>, <button> is usually user-facing; values in class/id/data-* are usually technical
- Preserve tone and formality appropriate for the application domain
- Use natural, idiomatic expressions in target languages

"""

        # Add each request
        for item in items:
            text = self._escape_xml(item["text"])

            # Extract context from occurrences
            contexts = []
            for occurrence in item.get("occurrences", []):
                for position in occurrence.get("positions", []):
                    context_lines = position.get("context", [])
                    if context_lines:
                        # Join context lines as plain text (preserve structure)
                        context_text = "\n".join(context_lines)
                        contexts.append(context_text)

            # Use first context (usually sufficient)
            reference = self._escape_xml(contexts[0]) if contexts else ""

            prompt += f"""<request>
<text>{text}</text>
<reference>
{reference}
</reference>
</request>

"""

        # Add response format instructions
        prompt += f"""# Response Format
Return one <response> block for each <request>, maintaining the same order.
Each response must include the exact original <text> for matching.

Example for user-facing text:
<response>
<text>original text here</text>
<translations>
{lang_descriptions}
</translations>
</response>

Example for technical/non-translatable text:
<response>
<text>btn-primary</text>
<translations>false</translations>
</response>

IMPORTANT:
- Return ONLY <response> blocks, no additional commentary
- The <text> in each response must exactly match the <text> from the request
- Maintain the order of requests in your responses
"""

        return prompt

    @staticmethod
    def _escape_xml(text: str) -> str:
        """
        Escape XML special characters.

        Args:
            text: Text to escape

        Returns:
            XML-escaped text
        """
        return html.escape(text, quote=False)

    @staticmethod
    def parse_xml_responses(response_text: str, items: List[Dict], languages: List[Tuple[str, str]]) -> List[Dict]:
        """
        Parse XML responses and match with original items.

        Args:
            response_text: XML response from AI
            items: Original items list
            languages: List of target languages

        Returns:
            List of items with translations added
        """
        results = {}

        # Extract all <response> blocks
        response_pattern = r"<response>(.*?)</response>"
        for response_match in re.finditer(response_pattern, response_text, re.DOTALL | re.IGNORECASE):
            content = response_match.group(1)

            # Extract <text>
            text_match = re.search(r"<text>(.*?)</text>", content, re.DOTALL)
            if not text_match:
                continue

            # Unescape XML entities
            original_text = html.unescape(text_match.group(1).strip())

            # Check <translations>
            if re.search(r"<translations>\s*false\s*</translations>", content, re.IGNORECASE):
                results[original_text] = False
            else:
                # Extract language tags
                translations = {}
                for lang_code, _ in languages:
                    lang_pattern = f"<{lang_code}>(.*?)</{lang_code}>"
                    lang_match = re.search(lang_pattern, content, re.DOTALL)
                    if lang_match:
                        translations[lang_code] = html.unescape(lang_match.group(1).strip())

                if translations:
                    results[original_text] = translations

        # Match results with original items
        output = []
        for item in items:
            text = item["text"]
            if text in results:
                output_item = {"text": text, "translations": results[text]}
                output.append(output_item)
            else:
                # Item not found in response (error case)
                # Return without translation
                output.append({"text": text})

        return output
