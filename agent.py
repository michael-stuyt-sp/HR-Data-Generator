import ollama
import json
import asyncio
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

def _ollama_chat(system: str, user: str) -> str:
    try:
        response = ollama.chat(
            model="llama3.2:3b",
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
# Provider dispatch
# ---------------------------------------------------------------------------

def _chat(system: str, user: str, provider: str) -> str:
    if provider == "apfel":
        return _apfel_chat(system, user)
    return _ollama_chat(system, user)


def _parse_json(content: str, context: str) -> dict | list:
    content = _strip_markdown_fences(content)
    try:
        return json.loads(content)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"LLM returned invalid JSON for {context}.\n"
            f"  {e}\n  Raw response: {content[:200]}"
        ) from e


def research_company(company_name: str, provider: str = "ollama") -> dict:
    content = _chat(
        system=SYSTEM_PROMPT,
        user=RESEARCH_PROMPT.format(company_name=company_name),
        provider=provider,
    )
    return _parse_json(content, "company research")


def get_job_titles(industry: str, provider: str = "ollama") -> list[str]:
    content = _chat(
        system="You are a job title expert. Return only a JSON array of 15-20 realistic job titles for the given industry.",
        user=JOB_TITLES_PROMPT.format(industry=industry),
        provider=provider,
    )
    return _parse_json(content, "job titles")


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class CompanyAgent:
    def __init__(self, company_name: str, provider: str = "ollama"):
        self.company_name = company_name
        self.provider = provider
        self.profile: CompanyProfile | None = None

    def research(self) -> CompanyProfile:
        print(f"Researching {self.company_name} (provider: {self.provider})...")
        company_info = research_company(self.company_name, self.provider)

        print(f"Found: {company_info['industry']} company")
        print(f"Generating job titles for {company_info['industry']} industry...")
        job_titles = get_job_titles(company_info["industry"], self.provider)

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
