"""CrewAI crew definition for content pipeline."""

import os
from pathlib import Path
from crewai import Agent, Crew, Process, Task
from tools import SearxngSearchTool, SearxngMultiSearchTool, WebCrawlTool
import yaml

CONFIG_DIR = Path(__file__).parent.parent / "config"

def get_llm(model: str = None):
    """Get LLM instance for agent."""
    from crewai import LLM
    model = model or os.environ.get("CREWAI_DEFAULT_MODEL", "gemini/gemini-3.1-flash-lite")
    return LLM(model=model, temperature=0.7)

class IdeationCrew:
    """Phase 1: Ideation + Research."""
    def __init__(self):
        with open(CONFIG_DIR / "agents.yaml") as f:
            self.agents_config = yaml.safe_load(f)
        with open(CONFIG_DIR / "tasks.yaml") as f:
            self.tasks_config = yaml.safe_load(f)

    def crew(self) -> Crew:
        ide_agent = Agent(config=self.agents_config["ide_agent"], llm=get_llm(), verbose=True)
        research_agent = Agent(
            config=self.agents_config["research_agent"],
            tools=[SearxngSearchTool(), SearxngMultiSearchTool(), WebCrawlTool()],
            llm=get_llm(),
            verbose=True
        )
        
        ideation_task = Task(
            description=self.tasks_config["ideation_task"]["description"],
            expected_output=self.tasks_config["ideation_task"]["expected_output"],
            agent=ide_agent
        )
        research_task = Task(
            description=self.tasks_config["research_task"]["description"],
            expected_output=self.tasks_config["research_task"]["expected_output"],
            agent=research_agent
        )
        
        return Crew(
            agents=[ide_agent, research_agent],
            tasks=[ideation_task, research_task],
            process=Process.sequential,
            verbose=True
        )

class ArticleCrew:
    """Phase 2: Write, Review, Edit SINGLE article."""
    def __init__(self):
        with open(CONFIG_DIR / "agents.yaml") as f:
            self.agents_config = yaml.safe_load(f)
        with open(CONFIG_DIR / "tasks.yaml") as f:
            self.tasks_config = yaml.safe_load(f)

    def crew(self) -> Crew:
        # Load the updated agents
        writer_agent = Agent(config=self.agents_config["writer_agent"], llm=get_llm("gemini/gemini-3.5-flash"), verbose=True)
        eeat_trust_reviewer = Agent(config=self.agents_config["eeat_trust_reviewer"], llm=get_llm(), verbose=True)
        seo_ux_reviewer = Agent(config=self.agents_config["seo_ux_reviewer"], llm=get_llm(), verbose=True)
        people_first_reviewer = Agent(config=self.agents_config["people_first_reviewer"], llm=get_llm(), verbose=True)
        review_aggregator = Agent(config=self.agents_config["review_aggregator"], llm=get_llm(), verbose=True)
        editor_agent = Agent(config=self.agents_config["editor_agent"], llm=get_llm("gemini/gemini-3.5-flash"), verbose=True)

        # Load the tasks
        writing_task = Task(
            description=self.tasks_config["writing_task"]["description"],
            expected_output=self.tasks_config["writing_task"]["expected_output"],
            agent=writer_agent
        )
        eeat_trust_review_task = Task(
            description=self.tasks_config["eeat_trust_review_task"]["description"],
            expected_output=self.tasks_config["eeat_trust_review_task"]["expected_output"],
            agent=eeat_trust_reviewer,
            context=[writing_task]
        )
        seo_ux_review_task = Task(
            description=self.tasks_config["seo_ux_review_task"]["description"],
            expected_output=self.tasks_config["seo_ux_review_task"]["expected_output"],
            agent=seo_ux_reviewer,
            context=[writing_task]
        )
        people_first_review_task = Task(
            description=self.tasks_config["people_first_review_task"]["description"],
            expected_output=self.tasks_config["people_first_review_task"]["expected_output"],
            agent=people_first_reviewer,
            context=[writing_task]
        )
        
        # Aggregator task now only takes context from the 3 new reviewers
        aggregate_review_task = Task(
            description=self.tasks_config["aggregate_review_task"]["description"],
            expected_output=self.tasks_config["aggregate_review_task"]["expected_output"],
            agent=review_aggregator,
            context=[eeat_trust_review_task, seo_ux_review_task, people_first_review_task]
        )
        
        editing_task = Task(
            description=self.tasks_config["editing_task"]["description"],
            expected_output=self.tasks_config["editing_task"]["expected_output"],
            agent=editor_agent,
            context=[writing_task, aggregate_review_task]
        )

        return Crew(
            agents=[
                writer_agent, 
                eeat_trust_reviewer, 
                seo_ux_reviewer, 
                people_first_reviewer, 
                review_aggregator, 
                editor_agent
            ],
            tasks=[
                writing_task,
                eeat_trust_review_task,
                seo_ux_review_task,
                people_first_review_task,
                aggregate_review_task,
                editing_task
            ],
            process=Process.sequential,
            verbose=True
        )
