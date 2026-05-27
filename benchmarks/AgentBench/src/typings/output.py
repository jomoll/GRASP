from typing import Union, List, Dict, Any

from pydantic import BaseModel, root_validator

from . import ChatHistoryItem
from .general import JSONSerializable, SampleIndex
from .status import SampleStatus, AgentOutputStatus


class TaskOutput(BaseModel):
    index: Union[None, SampleIndex] = None
    status: SampleStatus = SampleStatus.RUNNING
    result: JSONSerializable = None
    history: Union[None, List[ChatHistoryItem]] = None
    tools: Union[None, List[Dict[str, Any]]] = None


class TaskSampleExecutionResult(BaseModel):
    status: SampleStatus = SampleStatus.COMPLETED
    result: JSONSerializable = None


class AgentOutput(BaseModel):
    status: AgentOutputStatus = AgentOutputStatus.NORMAL
    content: Union[str, None] = None
    messages: Union[List[Dict[str, Any]], None] = None

    # at least one of them should be not None
    @root_validator(pre=False, skip_on_failure=True)
    def post_validate(cls, instance: dict):
        assert (
            instance.get("status") is not AgentOutputStatus.NORMAL
            or instance.get("content") is not None
            or instance.get("messages") is not None
        ), "If status is NORMAL, content or messages should not be None"
        return instance


class TaskClientOutput(BaseModel):
    error: Union[str, None] = None
    info: Union[str, None] = None
    output: Union[TaskOutput, None] = None
