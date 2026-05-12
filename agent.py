import ollama
import json
import asyncio
import os
from company import CompanyProfile

SYSTEM_PROMPT = """You are a company research assistant. Use the provided tools to gather information about a company."""

RESEARCH_PROMPT = """Research the company "{company_name}" and return a JSON object with:
- "industry": The primary industry (e.g., "Technology", "Healthcare", "Finance")
- "description": A brief description of what the company does (1-2 sentences)
- "departments": List of 6-8 typical departments for this company
- "locations": List of 3-5 major office locations with city, country, and a company domain

Return ONLY valid JSON, no markdown or explanation."""

JOB_TITLES_PROMPT = (
    "List 15-20 realistic job titles for a {industry} company. "
    "Include a mix of entry-level, mid-level, and senior positions. "
    "Return ONLY a JSON array of strings, nothing else."
)

# Default models per cloud provider
DEFAULT_MODELS = {
    "openai": "gpt-4o-mini",
    "anthropic": "claude-3-5-haiku-latest",
    "gemini": "gemini-2.0-flash",
}


def _strip_markdown_fences(content: str) -> str:
    """Strip markdown code fences that LLMs sometimes wrap JSON in."""
    content = content.strip()
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
        content = content.strip()
    return content


# ---------------------------------------------------------------------------
# Ollama backend
# ---------------------------------------------------------------------------

def _ollama_chat(system: str, user: str, model: str = "llama3.2:3b") -> str:
    try:
        response = ollama.chat(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            options={"temperature": 0.3},
        )
    except Exception as e:
        raise RuntimeError(
            f"Could not connect to Ollama. Make sure it is running locally.\n  {e}"
        ) from e
    return response["message"]["content"]


# ---------------------------------------------------------------------------
# Apfel (Apple Foundation Models) backend
# ---------------------------------------------------------------------------

async def _apfel_chat_async(system: str, user: str) -> str:
    try:
        import apple_fm_sdk as fm
    except ImportError as e:
        raise RuntimeError(
            "apple-fm-sdk is not installed. Run: pip install apple-fm-sdk"
        ) from e

    model = fm.SystemLanguageModel()
    is_available, reason = model.is_available()
    if not is_available:
        raise RuntimeError(
            f"Apple Foundation Models not available: {reason}\n"
            "Make sure Apple Intelligence is enabled and you are running macOS 26+."
        )

    try:
        session = fm.LanguageModelSession(instructions=system, model=model)
        response = await session.respond(user)
        return str(response)
    except fm.ExceededContextWindowSizeError as e:
        raise ValueError(f"Prompt too long for Apple Foundation Models: {e}") from e
    except fm.GuardrailViolationError as e:
        raise ValueError(f"Apple Foundation Models guardrail violation: {e}") from e
    except Exception as e:
        raise RuntimeError(
            f"Apple Foundation Models generation error: {e}"
        ) from e


def _apfel_chat(system: str, user: str) -> str:
    return asyncio.run(_apfel_chat_async(system, user))


# ---------------------------------------------------------------------------
# OpenAI backend
# ---------------------------------------------------------------------------

def _openai_chat(system: str, user: str, model: str) -> str:
    try:
        from openai import OpenAI
    except ImportError as e:
        raise RuntimeError(
            "openai package is not installed. Run: pip install openai"
        ) from e

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY environment variable is not set."
        )

    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.3,
        )
    except Exception as e:
        raise RuntimeError(f"OpenAI API error: {e}") from e

    return response.choices[0].message.content


# ---------------------------------------------------------------------------
# Anthropic backend
# ---------------------------------------------------------------------------

def _anthropic_chat(system: str, user: str, model: str) -> str:
    try:
        import anthropic
    except ImportError as e:
        raise RuntimeError(
            "anthropic package is not installed. Run: pip install anthropic"
        ) from e

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY environment variable is not set."
        )

    try:
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=model,
            max_tokens=1024,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
    except Exception as e:
        raise RuntimeError(f"Anthropic API error: {e}") from e

    return response.content[0].text


# ---------------------------------------------------------------------------
# Google Gemini backend
# ---------------------------------------------------------------------------

def _gemini_chat(system: str, user: str, model: str) -> str:
    try:
        from google import generativeai as genai
    except ImportError as e:
        raise RuntimeError(
            "google-generativeai package is not installed. Run: pip install google-generativeai"
        ) from e

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY environment variable is not set."
        )

    try:
        genai.configure(api_key=api_key)
        gemini_model = genai.GenerativeModel(
            model_name=model,
            system_instruction=system,
            generation_config={"temperature": 0.3},
        )
        response = gemini_model.generate_content(user)
    except Exception as e:
        raise RuntimeError(f"Gemini API error: {e}") from e

    return response.text


# ---------------------------------------------------------------------------
# Provider dispatch
# ---------------------------------------------------------------------------

def _chat(system: str, user: str, provider: str, model: str | None = None) -> str:
    if provider == "apfel":
        return _apfel_chat(system, user)
    if provider == "openai":
        return _openai_chat(system, user, model or DEFAULT_MODELS["openai"])
    if provider == "anthropic":
        return _anthropic_chat(system, user, model or DEFAULT_MODELS["anthropic"])
    if provider == "gemini":
        return _gemini_chat(system, user, model or DEFAULT_MODELS["gemini"])
    # Default: ollama
    return _ollama_chat(system, user, model or "llama3.2:3b")


def _parse_json(content: str, context: str) -> dict | list:
    content = _strip_markdown_fences(content)
    try:
        return json.loads(content)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"LLM returned invalid JSON for {context}.\n"
            f"  {e}\n  Raw response: {content[:200]}"
        ) from e


def research_company(company_name: str, provider: str = "ollama", model: str | None = None) -> dict:
    content = _chat(
        system=SYSTEM_PROMPT,
        user=RESEARCH_PROMPT.format(company_name=company_name),
        provider=provider,
        model=model,
    )
    return _parse_json(content, "company research")


def get_job_titles(industry: str, provider: str = "ollama", model: str | None = None) -> list[str]:
    content = _chat(
        system="You are a job title expert. Return only a JSON array of 15-20 realistic job titles for the given industry.",
        user=JOB_TITLES_PROMPT.format(industry=industry),
        provider=provider,
        model=model,
    )
    return _parse_json(content, "job titles")


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class CompanyAgent:
    def __init__(self, company_name: str, provider: str = "ollama", model: str | None = None):
        self.company_name = company_name
        self.provider = provider
        self.model = model
        self.profile: CompanyProfile | None = None

    def research(self) -> CompanyProfile:
        print(f"Researching {self.company_name} (provider: {self.provider}"
              + (f", model: {self.model}" if self.model else "") + ")...")
        company_info = research_company(self.company_name, self.provider, self.model)

        print(f"Found: {company_info['industry']} company")
        print(f"Generating job titles for {company_info['industry']} industry...")
        job_titles = get_job_titles(company_info["industry"], self.provider, self.model)

        locations = []
        company_slug = self.company_name.lower().replace(" ", "").replace(".", "")
        country_fallbacks = {
            "san francisco": "United States",
            "new york": "United States",
            "cupertino": "United States",
            "austin": "United States",
            "london": "United Kingdom",
            "berlin": "Germany",
            "tokyo": "Japan",
            "sydney": "Australia",
            "toronto": "Canada",
            "dublin": "Ireland",
        }
        for loc in company_info.get("locations", []):
            city = loc.get("city", "")
            country = loc.get("country", "")
            city_countries = {
                "ireland": "Ireland",
                "germany": "Germany",
                "france": "France",
                "spain": "Spain",
                "italy": "Italy",
                "japan": "Japan",
                "australia": "Australia",
                "canada": "Canada",
                "uk": "United Kingdom",
                "united kingdom": "United Kingdom",
                "usa": "United States",
                "united states": "United States",
                "mexico": "Mexico",
                "brazil": "Brazil",
                "china": "China",
                "india": "India",
                "singapore": "Singapore",
                "netherlands": "Netherlands",
                "sweden": "Sweden",
                "norway": "Norway",
                "denmark": "Denmark",
                "finland": "Finland",
                "poland": "Poland",
                "russia": "Russia",
                "korea": "South Korea",
            }
            city_lower = city.lower()
            default_cities = {
                "ireland": "Dublin",
                "germany": "Berlin",
                "france": "Paris",
                "uk": "London",
                "united kingdom": "London",
                "usa": "New York",
                "united states": "New York",
                "japan": "Tokyo",
                "australia": "Sydney",
                "canada": "Toronto",
                "singapore": "Singapore",
                "netherlands": "Amsterdam",
                "sweden": "Stockholm",
                "norway": "Oslo",
                "denmark": "Copenhagen",
                "finland": "Helsinki",
                "spain": "Madrid",
                "italy": "Milan",
            }
            if city_lower in city_countries:
                country = city_countries[city_lower]
                city = default_cities.get(city_lower, country.split()[0])
            if not country or country.lower() == city.lower():
                if city.lower() in country_fallbacks:
                    country = country_fallbacks[city.lower()]
                else:
                    country = city if city else "United States"
            raw_domain = loc.get("domain", "")
            domain = raw_domain.replace("@", "").strip()
            if (
                not domain
                or not any(c.isalpha() for c in domain)
                or domain.startswith(".")
            ):
                domain = f"{company_slug}.com"
            elif company_slug not in domain:
                domain = f"{company_slug}.com"
            locations.append({"city": city, "country": country, "domain": domain})

        self.profile = CompanyProfile(
            name=self.company_name,
            industry=company_info["industry"],
            description=company_info.get("description", ""),
            job_titles=job_titles,
            departments=company_info.get("departments", ["General"]),
            office_locations=locations,
        )
        return self.profile

    def get_profile(self) -> CompanyProfile:
        if not self.profile:
            return self.research()
        return self.profile
