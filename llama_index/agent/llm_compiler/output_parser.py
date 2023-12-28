"""LLM Compiler Output Parser"""

import ast
import re
from typing import Any, Sequence, Union, List, Dict, Any
from llama_index.tools import BaseTool
from pydantic import BaseModel
from llama_index.agent.llm_compiler.schema import LLMCompilerParseResult, JoinerOutput
from llama_index.agent.llm_compiler.utils import get_graph_dict

THOUGHT_PATTERN = r"Thought: ([^\n]*)"
ACTION_PATTERN = r"\n*(\d+)\. (\w+)\((.*)\)(\s*#\w+\n)?"
# $1 or ${1} -> 1
ID_PATTERN = r"\$\{?(\d+)\}?"

END_OF_PLAN = "<END_OF_PLAN>"
JOINER_REPLAN = "Replan"

from llama_index.types import BaseOutputParser


def default_dependency_rule(idx, args: str):
    matches = re.findall(ID_PATTERN, args)
    numbers = [int(match) for match in matches]
    return idx in numbers


class LLMCompilerPlanParser(BaseOutputParser):
    """LLM Compiler plan output parser.

    Directly adapted from source code: https://github.com/SqueezeAILab/LLMCompiler/blob/main/src/llm_compiler/output_parser.py.

    """

    def __init__(self, tools: Sequence[BaseTool]):
        """Init params."""
        self.tools = tools

    def parse(self, text: str) -> Dict[str, Any]:
        # 1. search("Ronaldo number of kids") -> 1, "search", '"Ronaldo number of kids"'
        # pattern = r"(\d+)\. (\w+)\(([^)]+)\)"
        pattern = rf"(?:{THOUGHT_PATTERN}\n)?{ACTION_PATTERN}"
        matches = re.findall(pattern, text)

        # convert matches to a list of LLMCompilerParseResult
        results: List[LLMCompilerParseResult] = []
        for match in matches:
            thought, idx, tool_name, args, _ = match
            idx = int(idx)
            results.append(
                LLMCompilerParseResult(
                    thought=thought, idx=idx, tool_name=tool_name, args=args
                )
            )

        # get graph dict
        graph_dict = get_graph_dict(results, self.tools)

        return graph_dict


### Helper functions


class LLMCompilerJoinerParser(BaseOutputParser):
    """LLM Compiler output parser for the join step.

    Adapted from _parse_joiner_output in
    https://github.com/SqueezeAILab/LLMCompiler/blob/main/src/llm_compiler/llm_compiler.py
    
    """

    def parse(self, text: str) -> JoinerOutput:
        """Parse"""
        thought, answer, is_replan = "", "", False  # default values
        raw_answers = text.split("\n")
        for ans in raw_answers:
            if ans.startswith("Action:"):
                answer = ans[ans.find("(") + 1 : ans.find(")")]
                is_replan = JOINER_REPLAN in ans
            elif ans.startswith("Thought:"):
                thought = ans.split("Thought:")[1].strip()
        return JoinerOutput(thought=thought, answer=answer, is_replan=is_replan)
    

