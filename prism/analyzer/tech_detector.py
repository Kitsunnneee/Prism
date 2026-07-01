"""
Tech stack detection from employee profiles.
Core reverse engineering logic.
"""

import re
from typing import List, Dict, Set
from collections import defaultdict

from prism.models.company import Employee, TechSignal


class TechStackDetector:
    """
    Analyzes employee profiles to infer company tech stack.

    Strategy:
    1. Extract tech mentions from titles, headlines, skills
    2. Prefer engineering-relevant profiles when sampling
    3. Score confidence based on profile coverage
    """

    # Technology keywords mapped to categories
    # This is our knowledge base of what to look for
    TECH_KEYWORDS = {
        "languages": {
            "python": ["python", "py"],
            "javascript": ["javascript", "js", "node.js", "nodejs"],
            "typescript": ["typescript", "ts"],
            "java": ["java"],
            "go": ["golang", "go"],
            "rust": ["rust"],
            "ruby": ["ruby", "rails"],
            "c++": ["c++", "cpp"],
            "c#": ["c#", "csharp", ".net"],
            "php": ["php"],
            "swift": ["swift"],
            "kotlin": ["kotlin"],
            "scala": ["scala"],
        },
        "databases": {
            "postgresql": ["postgres", "postgresql", "psql"],
            "mysql": ["mysql"],
            "mongodb": ["mongodb", "mongo"],
            "redis": ["redis"],
            "elasticsearch": ["elasticsearch", "elastic"],
            "cassandra": ["cassandra"],
            "dynamodb": ["dynamodb"],
            "sqlite": ["sqlite"],
        },
        "frameworks": {
            "react": ["react", "reactjs", "react.js"],
            "vue": ["vue", "vuejs", "vue.js"],
            "angular": ["angular"],
            "django": ["django"],
            "flask": ["flask"],
            "fastapi": ["fastapi"],
            "spring": ["spring boot", "spring"],
            "express": ["express", "expressjs"],
            "nextjs": ["next.js", "nextjs"],
        },
        "infrastructure": {
            "aws": ["aws", "amazon web services"],
            "gcp": ["gcp", "google cloud"],
            "azure": ["azure", "microsoft azure"],
            "kubernetes": ["kubernetes", "k8s"],
            "docker": ["docker"],
            "terraform": ["terraform"],
            "ansible": ["ansible"],
        },
        "tools": {
            "git": ["git", "github", "gitlab"],
            "ci/cd": ["jenkins", "circleci", "github actions", "gitlab ci"],
            "datadog": ["datadog"],
            "grafana": ["grafana"],
            "prometheus": ["prometheus"],
        }
    }

    TECH_ROLE_KEYWORDS = [
        "engineer",
        "engineering",
        "developer",
        "software",
        "backend",
        "frontend",
        "full stack",
        "platform",
        "infrastructure",
        "data",
        "machine learning",
        "ml",
        "ai",
        "security",
        "devops",
        "sre",
        "architect",
        "technical",
        "product engineer",
    ]

    NON_TECH_ROLE_KEYWORDS = [
        "advisor",
        "investor",
        "board",
        "sales",
        "revenue",
        "marketing",
        "operations",
        "partnerships",
        "recruiting",
        "talent",
        "finance",
        "legal",
        "chief revenue",
    ]

    def __init__(self):
        """
        Build reverse lookup: keyword -> (tech_name, category)
        This lets us quickly find what tech a keyword belongs to.
        """
        self.keyword_map: Dict[str, tuple] = {}

        for category, techs in self.TECH_KEYWORDS.items():
            for tech_name, keywords in techs.items():
                for keyword in keywords:
                    # Lowercase for case-insensitive matching
                    self.keyword_map[keyword.lower()] = (tech_name, category)

    def detect_tech_stack(self, employees: List[Employee]) -> List[TechSignal]:
        """
        Main analysis function.
        Takes employee list, returns detected technologies with confidence scores.

        Algorithm:
        1. Scan all employees for tech mentions
        2. Count unique employee profiles per technology
        3. Calculate confidence based on profile coverage
        4. Return sorted by confidence
        """
        if not employees:
            return []

        # Track one evidence example per employee per technology.
        tech_evidence: Dict[str, List[str]] = defaultdict(list)
        tech_employee_ids: Dict[str, Set[str]] = defaultdict(set)

        # Track: tech_name -> category
        tech_categories: Dict[str, str] = {}

        # Analyze each employee
        for employee in employees:
            detected = self._extract_tech_from_employee(employee)
            employee_key = str(employee.crustdata_person_id or employee.name or id(employee))
            employee_evidence: Dict[str, str] = {}

            for tech_name, category, evidence in detected:
                tech_categories[tech_name] = category
                employee_evidence.setdefault(tech_name, evidence)

            for tech_name, evidence in employee_evidence.items():
                tech_employee_ids[tech_name].add(employee_key)
                tech_evidence[tech_name].append(evidence)

        # Convert to TechSignal objects with confidence scores
        signals = []
        total_employees = len(employees)

        for tech_name, evidence_list in tech_evidence.items():
            # Confidence = what fraction of sampled employees mention this tech
            # If 8 out of 10 employees mention Python, confidence = 0.8
            employee_count = len(tech_employee_ids[tech_name])
            confidence = employee_count / total_employees

            signal = TechSignal(
                technology=tech_name,
                confidence=round(confidence, 2),
                evidence_count=employee_count,
                evidence=evidence_list[:5],  # Keep top 5 examples
                category=tech_categories[tech_name]
            )
            signals.append(signal)

        # Sort by confidence (highest first)
        signals.sort(reverse=True)

        return signals

    def select_relevant_employees(
        self,
        employees: List[Employee],
        limit: int
    ) -> List[Employee]:
        """
        Prefer engineering-heavy profiles when the API returns a broad employee mix.
        """
        if len(employees) <= limit:
            return employees

        ranked = sorted(
            employees,
            key=self._employee_relevance_score,
            reverse=True
        )
        return ranked[:limit]

    def _extract_tech_from_employee(self, employee: Employee) -> List[tuple]:
        """
        Extract all tech mentions from a single employee profile.

        Returns:
            List of (tech_name, category, evidence_string) tuples
        """
        detected = []

        # Combine all text fields to search
        search_texts = [
            ("title", employee.current_title or ""),
            ("headline", employee.headline or ""),
        ]

        # Add skills
        for skill in employee.skills:
            search_texts.append(("skill", skill))

        # Add job titles from experience
        for exp in employee.experience:
            if exp.title:
                search_texts.append(("past_title", exp.title))
            if exp.description:
                search_texts.append(("job_description", exp.description))

        # Search for tech keywords in all text
        for source, text in search_texts:
            if not text:
                continue

            text_lower = text.lower()

            # Check against all known keywords
            for keyword, (tech_name, category) in self.keyword_map.items():
                # Use word boundaries to avoid false matches
                # e.g., "go" shouldn't match "google"
                pattern = r'\b' + re.escape(keyword) + r'\b'

                if re.search(pattern, text_lower):
                    evidence = f"{employee.name or 'Employee'} ({source}): {text[:80]}"
                    detected.append((tech_name, category, evidence))

        return detected

    def _employee_relevance_score(self, employee: Employee) -> int:
        text_parts = [
            employee.current_title or "",
            employee.headline or "",
            " ".join(employee.skills),
            " ".join(
                part
                for exp in employee.experience
                for part in [exp.title or "", exp.description or ""]
            ),
        ]
        text = " ".join(text_parts).lower()

        score = len(self._extract_tech_from_employee(employee)) * 5

        for keyword in self.TECH_ROLE_KEYWORDS:
            if keyword in text:
                score += 3

        for keyword in self.NON_TECH_ROLE_KEYWORDS:
            if keyword in text:
                score -= 2

        return score

    def group_by_category(self, signals: List[TechSignal]) -> Dict[str, List[TechSignal]]:
        """
        Group detected technologies by category for better display.

        Returns:
            Dict mapping category name to list of signals
        """
        grouped = defaultdict(list)

        for signal in signals:
            grouped[signal.category].append(signal)

        # Sort each category by confidence
        for category in grouped:
            grouped[category].sort(reverse=True)

        return dict(grouped)
