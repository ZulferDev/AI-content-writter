"""Google Search Grounding tool for AI Pipeline."""

import os
from typing import Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field


class GoogleSearchInput(BaseModel):
    query: str = Field(description="Search query untuk riset konten")


class GoogleSearchGroundingTool(BaseTool):
    name: str = "google_search"
    description: str = (
        "Cari informasi di web menggunakan Google Search Grounding. "
        "Kembalikan ringkasan informatif yang mencakup fakta utama, "
        "data pendukung, dan sumber informasi. Gunakan tool ini untuk "
        "meriset topik artikel, mencari data terkini, dan mendapatkan "
        "informasi terverifikasi."
    )
    args_schema: Type[BaseModel] = GoogleSearchInput

    def _run(self, query: str) -> str:
        from google import genai
        from google.genai import types

        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            return "Error: GEMINI_API_KEY tidak ditemukan di environment."

        client = genai.Client(api_key=api_key)

        grounding_tool = types.Tool(google_search=types.GoogleSearch())
        config = types.GenerateContentConfig(tools=[grounding_tool])

        prompt = (
            "Lakukan riset menyeluruh tentang topik berikut:\n\n"
            f"{query}\n\n"
            "Berikan ringkasan informatif yang mencakup fakta utama, "
            "data pendukung, dan referensi. Cantumkan sumber informasi."
        )

        try:
            response = client.models.generate_content(
                model="gemini-3.1-flash-lite",
                contents=prompt,
                config=config,
            )
            return response.text
        except Exception as e:
            return f"Error saat melakukan Google Search Grounding: {e}"
