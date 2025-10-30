# pylint: disable=C0116
"""Adapter layer between Google A2A SDK types and Restate models."""

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

# Google A2A SDK imports
from a2a.types import (
    AgentCard as A2AAgentCard,
    Message as A2AMessage,
    Part as A2APart,
    Task as A2ATask,
    TaskState as A2ATaskState,
    TaskStatus as A2ATaskStatus,
    TextPart as A2ATextPart,
    DataPart as A2ADataPart,
    FilePart as A2AFilePart,
    Artifact as A2AArtifact,
    AgentSkill as A2AAgentSkill,
    AgentCapabilities as A2AAgentCapabilities,
)

# Local Restate models
from .models import (
    AgentCard,
    Message,
    Part,
    Task,
    TaskState,
    TaskStatus,
    TextPart,
    DataPart,
    FilePart,
    Artifact,
    AgentSkill,
    AgentCapabilities,
    FileContent,
)

logger = logging.getLogger(__name__)


class A2ASDKAdapter:
    """Adapter for converting between Google A2A SDK types and Restate models."""

    @staticmethod
    def task_state_to_sdk(state: TaskState) -> A2ATaskState:
        """Convert Restate TaskState to A2A SDK TaskState."""
        mapping = {
            TaskState.SUBMITTED: A2ATaskState.SUBMITTED,
            TaskState.WORKING: A2ATaskState.WORKING,
            TaskState.INPUT_REQUIRED: A2ATaskState.INPUT_REQUIRED,
            TaskState.COMPLETED: A2ATaskState.COMPLETED,
            TaskState.CANCELED: A2ATaskState.CANCELED,
            TaskState.FAILED: A2ATaskState.FAILED,
            TaskState.REJECTED: A2ATaskState.REJECTED,
            TaskState.AUTH_REQUIRED: A2ATaskState.AUTH_REQUIRED,
            TaskState.UNKNOWN: A2ATaskState.UNKNOWN,
        }
        return mapping.get(state, A2ATaskState.UNKNOWN)

    @staticmethod
    def task_state_from_sdk(state: A2ATaskState) -> TaskState:
        """Convert A2A SDK TaskState to Restate TaskState."""
        mapping = {
            A2ATaskState.SUBMITTED: TaskState.SUBMITTED,
            A2ATaskState.WORKING: TaskState.WORKING,
            A2ATaskState.INPUT_REQUIRED: TaskState.INPUT_REQUIRED,
            A2ATaskState.COMPLETED: TaskState.COMPLETED,
            A2ATaskState.CANCELED: TaskState.CANCELED,
            A2ATaskState.FAILED: TaskState.FAILED,
            A2ATaskState.REJECTED: TaskState.REJECTED,
            A2ATaskState.AUTH_REQUIRED: TaskState.AUTH_REQUIRED,
            A2ATaskState.UNKNOWN: TaskState.UNKNOWN,
        }
        return mapping.get(state, TaskState.UNKNOWN)

    @staticmethod
    def part_to_sdk(part: Part) -> A2APart:
        """Convert Restate Part to A2A SDK Part."""
        if isinstance(part, TextPart):
            return A2ATextPart(
                text=part.text,
                metadata=part.metadata,
            )
        elif isinstance(part, DataPart):
            return A2ADataPart(
                data=part.data,
                metadata=part.metadata,
            )
        elif isinstance(part, FilePart):
            return A2AFilePart(
                file=part.file.model_dump(),
                metadata=part.metadata,
            )
        else:
            raise ValueError(f"Unsupported part type: {type(part)}")

    @staticmethod
    def part_from_sdk(part: A2APart) -> Part:
        """Convert A2A SDK Part to Restate Part."""
        if isinstance(part, A2ATextPart):
            return TextPart(
                text=part.text,
                metadata=part.metadata,
            )
        elif isinstance(part, A2ADataPart):
            return DataPart(
                data=part.data,
                metadata=part.metadata,
            )
        elif isinstance(part, A2AFilePart):
            # Convert the file dict back to FileContent
            file_data = part.file
            file_content = FileContent(
                name=file_data.get("name"),
                mimeType=file_data.get("mimeType"),
                bytes=file_data.get("bytes"),
                uri=file_data.get("uri"),
            )
            return FilePart(
                file=file_content,
                metadata=part.metadata,
            )
        else:
            raise ValueError(f"Unsupported A2A SDK part type: {type(part)}")

    @staticmethod
    def message_to_sdk(message: Message) -> A2AMessage:
        """Convert Restate Message to A2A SDK Message."""
        return A2AMessage(
            message_id=message.message_id,
            role=message.role,
            parts=[A2ASDKAdapter.part_to_sdk(part) for part in message.parts],
            metadata=message.metadata,
        )

    @staticmethod
    def message_from_sdk(message: A2AMessage) -> Message:
        """Convert A2A SDK Message to Restate Message."""
        return Message(
            message_id=message.message_id,
            role=message.role,
            parts=[A2ASDKAdapter.part_from_sdk(part) for part in message.parts],
            metadata=message.metadata,
        )

    @staticmethod
    def task_status_to_sdk(status: TaskStatus) -> A2ATaskStatus:
        """Convert Restate TaskStatus to A2A SDK TaskStatus."""
        return A2ATaskStatus(
            state=A2ASDKAdapter.task_state_to_sdk(status.state),
            message=(
                A2ASDKAdapter.message_to_sdk(status.message)
                if status.message
                else None
            ),
            timestamp=status.timestamp.isoformat(),
        )

    @staticmethod
    def task_status_from_sdk(status: A2ATaskStatus) -> TaskStatus:
        """Convert A2A SDK TaskStatus to Restate TaskStatus."""
        return TaskStatus(
            state=A2ASDKAdapter.task_state_from_sdk(status.state),
            message=(
                A2ASDKAdapter.message_from_sdk(status.message)
                if status.message
                else None
            ),
            timestamp=datetime.fromisoformat(status.timestamp),
        )

    @staticmethod
    def artifact_to_sdk(artifact: Artifact) -> A2AArtifact:
        """Convert Restate Artifact to A2A SDK Artifact."""
        return A2AArtifact(
            name=artifact.name,
            description=artifact.description,
            parts=[A2ASDKAdapter.part_to_sdk(part) for part in artifact.parts],
            metadata=artifact.metadata,
            index=artifact.index,
            append=artifact.append,
            lastChunk=artifact.lastChunk,
        )

    @staticmethod
    def artifact_from_sdk(artifact: A2AArtifact) -> Artifact:
        """Convert A2A SDK Artifact to Restate Artifact."""
        return Artifact(
            name=artifact.name,
            description=artifact.description,
            parts=[A2ASDKAdapter.part_from_sdk(part) for part in artifact.parts],
            metadata=artifact.metadata,
            index=artifact.index,
            append=artifact.append,
            lastChunk=artifact.lastChunk,
        )

    @staticmethod
    def task_to_sdk(task: Task) -> A2ATask:
        """Convert Restate Task to A2A SDK Task."""
        return A2ATask(
            id=task.id,
            context_id=task.sessionId,
            status=A2ASDKAdapter.task_status_to_sdk(task.status),
            artifacts=(
                [A2ASDKAdapter.artifact_to_sdk(artifact) for artifact in task.artifacts]
                if task.artifacts
                else None
            ),
            history=(
                [A2ASDKAdapter.message_to_sdk(message) for message in task.history]
                if task.history
                else None
            ),
            metadata=task.metadata,
        )

    @staticmethod
    def task_from_sdk(task: A2ATask) -> Task:
        """Convert A2A SDK Task to Restate Task."""
        return Task(
            id=task.id,
            sessionId=task.sessionId,
            status=A2ASDKAdapter.task_status_from_sdk(task.status),
            artifacts=(
                [A2ASDKAdapter.artifact_from_sdk(artifact) for artifact in task.artifacts]
                if task.artifacts
                else None
            ),
            history=(
                [A2ASDKAdapter.message_from_sdk(message) for message in task.history]
                if task.history
                else None
            ),
            metadata=task.metadata,
        )

    @staticmethod
    def agent_capabilities_to_sdk(capabilities: AgentCapabilities) -> A2AAgentCapabilities:
        """Convert Restate AgentCapabilities to A2A SDK AgentCapabilities."""
        return A2AAgentCapabilities(
            streaming=capabilities.streaming,
            pushNotifications=capabilities.pushNotifications,
            stateTransitionHistory=capabilities.stateTransitionHistory,
        )

    @staticmethod
    def agent_capabilities_from_sdk(capabilities: A2AAgentCapabilities) -> AgentCapabilities:
        """Convert A2A SDK AgentCapabilities to Restate AgentCapabilities."""
        return AgentCapabilities(
            streaming=capabilities.streaming,
            pushNotifications=capabilities.pushNotifications,
            stateTransitionHistory=capabilities.stateTransitionHistory,
        )

    @staticmethod
    def agent_skill_to_sdk(skill: AgentSkill) -> A2AAgentSkill:
        """Convert Restate AgentSkill to A2A SDK AgentSkill."""
        return A2AAgentSkill(
            id=skill.id,
            name=skill.name,
            description=skill.description,
            tags=skill.tags,
            examples=skill.examples,
            inputModes=skill.inputModes,
            outputModes=skill.outputModes,
        )

    @staticmethod
    def agent_skill_from_sdk(skill: A2AAgentSkill) -> AgentSkill:
        """Convert A2A SDK AgentSkill to Restate AgentSkill."""
        return AgentSkill(
            id=skill.id,
            name=skill.name,
            description=skill.description,
            tags=skill.tags,
            examples=skill.examples,
            inputModes=skill.inputModes,
            outputModes=skill.outputModes,
        )

    @staticmethod
    def agent_card_to_sdk(card: AgentCard) -> A2AAgentCard:
        """Convert Restate AgentCard to A2A SDK AgentCard."""
        return A2AAgentCard(
            name=card.name,
            description=card.description,
            url=card.url,
            provider=card.provider.model_dump() if card.provider else None,
            version=card.version,
            documentationUrl=card.documentationUrl,
            capabilities=A2ASDKAdapter.agent_capabilities_to_sdk(card.capabilities),
            authentication=card.authentication.model_dump() if card.authentication else None,
            defaultInputModes=card.defaultInputModes,
            defaultOutputModes=card.defaultOutputModes,
            skills=[A2ASDKAdapter.agent_skill_to_sdk(skill) for skill in card.skills],
        )

    @staticmethod
    def agent_card_from_sdk(card: A2AAgentCard) -> AgentCard:
        """Convert A2A SDK AgentCard to Restate AgentCard."""
        from .models import AgentProvider, AgentAuthentication

        return AgentCard(
            name=card.name,
            description=card.description,
            url=card.url,
            provider=AgentProvider(**card.provider) if card.provider else None,
            version=card.version,
            documentationUrl=card.documentationUrl,
            capabilities=A2ASDKAdapter.agent_capabilities_from_sdk(card.capabilities),
            authentication=AgentAuthentication(**card.authentication) if card.authentication else None,
            defaultInputModes=card.defaultInputModes,
            defaultOutputModes=card.defaultOutputModes,
            skills=[A2ASDKAdapter.agent_skill_from_sdk(skill) for skill in card.skills],
        )


class A2ASDKRestateWrapper:
    """Wrapper that provides A2A SDK-style interface with Restate durability."""

    def __init__(self, agent_card: AgentCard):
        self.agent_card = agent_card
        self.sdk_agent_card = A2ASDKAdapter.agent_card_to_sdk(agent_card)

    def get_agent_card(self) -> A2AAgentCard:
        """Get the agent card in A2A SDK format."""
        return self.sdk_agent_card

    def get_restate_agent_card(self) -> AgentCard:
        """Get the agent card in Restate format."""
        return self.agent_card

    async def convert_task_to_sdk(self, task: Task) -> A2ATask:
        """Convert a Restate task to A2A SDK format for external communication."""
        return A2ASDKAdapter.task_to_sdk(task)

    async def convert_task_from_sdk(self, task: A2ATask) -> Task:
        """Convert an A2A SDK task to Restate format for internal processing."""
        return A2ASDKAdapter.task_from_sdk(task)