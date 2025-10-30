# pylint: disable=C0116
"""Type validation and enhanced mapping for A2A SDK integration."""

import logging
from typing import Any, Dict, List, Optional, Type, TypeVar, Union
from pydantic import BaseModel, ValidationError

# Google A2A SDK imports
try:
    from a2a.types import (
        AgentCard as A2AAgentCard,
        Message as A2AMessage,
        Part as A2APart,
        Task as A2ATask,
        TaskState as A2ATaskState,
        TaskStatus as A2ATaskStatus,
    )
    A2A_SDK_AVAILABLE = True
except ImportError:
    A2A_SDK_AVAILABLE = False
    # Define placeholder types for development without SDK
    A2AAgentCard = Dict[str, Any]
    A2AMessage = Dict[str, Any]
    A2APart = Dict[str, Any]
    A2ATask = Dict[str, Any]
    A2ATaskState = str
    A2ATaskStatus = Dict[str, Any]

# Local Restate models
from .models import (
    AgentCard,
    Message,
    Part,
    Task,
    TaskState,
    TaskStatus,
)

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseModel)


class TypeValidationError(Exception):
    """Custom exception for type validation errors."""
    def __init__(self, message: str, validation_errors: Optional[List[str]] = None):
        self.message = message
        self.validation_errors = validation_errors or []
        super().__init__(self.format_message())

    def format_message(self) -> str:
        if self.validation_errors:
            return f"{self.message}. Validation errors: {'; '.join(self.validation_errors)}"
        return self.message


class A2ATypeValidator:
    """Enhanced type validator for A2A SDK integration."""

    @staticmethod
    def validate_sdk_availability():
        """Check if A2A SDK is available."""
        if not A2A_SDK_AVAILABLE:
            raise TypeValidationError("Google A2A SDK is not available. Install with: pip install a2a-sdk")

    @staticmethod
    def validate_restate_model(model_instance: BaseModel, expected_type: Type[T]) -> T:
        """Validate that a model instance matches the expected type."""
        if not isinstance(model_instance, expected_type):
            raise TypeValidationError(
                f"Expected {expected_type.__name__}, got {type(model_instance).__name__}"
            )
        return model_instance

    @staticmethod
    def validate_sdk_model(model_data: Any, expected_type_name: str) -> Any:
        """Validate SDK model data."""
        if not A2A_SDK_AVAILABLE:
            logger.warning("A2A SDK not available, skipping validation")
            return model_data

        # Add specific validation logic based on expected type
        if expected_type_name == "Task" and isinstance(model_data, dict):
            required_fields = ["id", "status"]
            missing_fields = [field for field in required_fields if field not in model_data]
            if missing_fields:
                raise TypeValidationError(
                    f"Missing required fields in {expected_type_name}",
                    [f"Missing field: {field}" for field in missing_fields]
                )

        return model_data

    @staticmethod
    def safe_convert_with_validation(
        source_data: Any,
        converter_func: callable,
        source_type_name: str,
        target_type_name: str
    ) -> Any:
        """Safely convert between types with comprehensive validation."""
        try:
            if source_data is None:
                return None

            # Validate source data
            if hasattr(source_data, 'model_validate'):
                # Pydantic model validation
                try:
                    source_data.model_validate(source_data.model_dump())
                except ValidationError as e:
                    raise TypeValidationError(
                        f"Source {source_type_name} validation failed",
                        [str(error) for error in e.errors()]
                    )

            # Perform conversion
            result = converter_func(source_data)

            # Validate result if it's a Pydantic model
            if hasattr(result, 'model_validate'):
                try:
                    result.model_validate(result.model_dump())
                except ValidationError as e:
                    raise TypeValidationError(
                        f"Target {target_type_name} validation failed after conversion",
                        [str(error) for error in e.errors()]
                    )

            logger.debug(f"Successfully converted {source_type_name} to {target_type_name}")
            return result

        except TypeValidationError:
            raise
        except Exception as e:
            raise TypeValidationError(
                f"Conversion from {source_type_name} to {target_type_name} failed: {str(e)}"
            )


class EnhancedA2ASDKAdapter:
    """Enhanced adapter with comprehensive validation and error handling."""

    def __init__(self, strict_validation: bool = True):
        self.strict_validation = strict_validation
        self.validator = A2ATypeValidator()

    def task_state_to_sdk(self, state: TaskState) -> Union[A2ATaskState, str]:
        """Convert Restate TaskState to A2A SDK TaskState with validation."""
        self.validator.validate_restate_model(state, TaskState)

        if A2A_SDK_AVAILABLE:
            mapping = {
                TaskState.SUBMITTED: A2ATaskState.SUBMITTED,
                TaskState.WORKING: A2ATaskState.WORKING,
                TaskState.INPUT_REQUIRED: A2ATaskState.INPUT_REQUIRED,
                TaskState.COMPLETED: A2ATaskState.COMPLETED,
                TaskState.CANCELED: A2ATaskState.CANCELED,
                TaskState.FAILED: A2ATaskState.FAILED,
                TaskState.UNKNOWN: A2ATaskState.UNKNOWN,
                TaskState.REJECTED: A2ATaskState.REJECTED
            }
            result = mapping.get(state, A2ATaskState.UNKNOWN)
        else:
            # Fallback to string representation
            result = state.value

        if self.strict_validation and result is None:
            raise TypeValidationError(f"Cannot convert TaskState {state} to SDK format")

        return result

    def task_state_from_sdk(self, state: Union[A2ATaskState, str]) -> TaskState:
        """Convert A2A SDK TaskState to Restate TaskState with validation."""
        if A2A_SDK_AVAILABLE and hasattr(state, 'value'):
            state_value = state.value
        else:
            state_value = str(state)

        mapping = {
            "submitted": TaskState.SUBMITTED,
            "working": TaskState.WORKING,
            "input-required": TaskState.INPUT_REQUIRED,
            "completed": TaskState.COMPLETED,
            "canceled": TaskState.CANCELED,
            "failed": TaskState.FAILED,
            "rejected": TaskState.REJECTED,
            "auth-required": TaskState.AUTH_REQUIRED,
            "unknown": TaskState.UNKNOWN,
        }

        result = mapping.get(state_value.lower(), TaskState.UNKNOWN)

        if self.strict_validation and result == TaskState.UNKNOWN and state_value != "unknown":
            raise TypeValidationError(f"Unknown TaskState value: {state_value}")

        return result

    def safe_task_to_sdk(self, task: Task) -> Dict[str, Any]:
        """Safely convert Restate Task to SDK format with comprehensive validation."""
        return self.validator.safe_convert_with_validation(
            task,
            self._convert_task_to_sdk_dict,
            "Restate Task",
            "A2A SDK Task"
        )

    def safe_task_from_sdk(self, task_data: Dict[str, Any]) -> Task:
        """Safely convert SDK task data to Restate Task with validation."""
        return self.validator.safe_convert_with_validation(
            task_data,
            self._convert_task_from_sdk_dict,
            "A2A SDK Task",
            "Restate Task"
        )

    def _convert_task_to_sdk_dict(self, task: Task) -> Dict[str, Any]:
        """Internal method to convert Task to SDK dict format."""
        self.validator.validate_restate_model(task, Task)

        result = {
            "id": task.id,
            "sessionId": task.sessionId,
            "status": {
                "state": self.task_state_to_sdk(task.status.state),
                "timestamp": task.status.timestamp.isoformat(),
                "message": (
                    self._convert_message_to_sdk_dict(task.status.message)
                    if task.status.message else None
                ),
            },
            "metadata": task.metadata,
        }

        if task.artifacts:
            result["artifacts"] = [
                self._convert_artifact_to_sdk_dict(artifact)
                for artifact in task.artifacts
            ]

        if task.history:
            result["history"] = [
                self._convert_message_to_sdk_dict(message)
                for message in task.history
            ]

        return result

    def _convert_task_from_sdk_dict(self, task_data: Dict[str, Any]) -> Task:
        """Internal method to convert SDK dict to Restate Task."""
        self.validator.validate_sdk_model(task_data, "Task")

        # Convert status
        status_data = task_data["status"]
        status = TaskStatus(
            state=self.task_state_from_sdk(status_data["state"]),
            timestamp=status_data["timestamp"],
            message=(
                self._convert_message_from_sdk_dict(status_data["message"])
                if status_data.get("message") else None
            ),
        )

        # Convert artifacts if present
        artifacts = None
        if task_data.get("artifacts"):
            from .models import Artifact
            artifacts = [
                self._convert_artifact_from_sdk_dict(artifact_data)
                for artifact_data in task_data["artifacts"]
            ]

        # Convert history if present
        history = None
        if task_data.get("history"):
            history = [
                self._convert_message_from_sdk_dict(message_data)
                for message_data in task_data["history"]
            ]

        return Task(
            id=task_data["id"],
            sessionId=task_data.get("sessionId"),
            status=status,
            artifacts=artifacts,
            history=history,
            metadata=task_data.get("metadata"),
        )

    def _convert_message_to_sdk_dict(self, message: Message) -> Dict[str, Any]:
        """Convert Restate Message to SDK dict format."""
        return {
            "role": message.role,
            "parts": [self._convert_part_to_sdk_dict(part) for part in message.parts],
            "metadata": message.metadata,
        }

    def _convert_message_from_sdk_dict(self, message_data: Dict[str, Any]) -> Message:
        """Convert SDK dict to Restate Message."""
        return Message(
            message_id=message_data["message_id"],
            role=message_data["role"],
            parts=[self._convert_part_from_sdk_dict(part) for part in message_data["parts"]],
            metadata=message_data.get("metadata"),
        )

    def _convert_part_to_sdk_dict(self, part: Part) -> Dict[str, Any]:
        """Convert Restate Part to SDK dict format."""
        from .models import TextPart, DataPart, FilePart

        if isinstance(part, TextPart):
            return {
                "type": "text",
                "text": part.text,
                "metadata": part.metadata,
            }
        elif isinstance(part, DataPart):
            return {
                "type": "data",
                "data": part.data,
                "metadata": part.metadata,
            }
        elif isinstance(part, FilePart):
            return {
                "type": "file",
                "file": part.file.model_dump(),
                "metadata": part.metadata,
            }
        else:
            raise TypeValidationError(f"Unsupported part type: {type(part)}")

    def _convert_part_from_sdk_dict(self, part_data: Dict[str, Any]) -> Part:
        """Convert SDK dict to Restate Part."""
        from .models import TextPart, DataPart, FilePart, FileContent

        part_type = part_data["type"]

        if part_type == "text":
            return TextPart(
                text=part_data["text"],
                metadata=part_data.get("metadata"),
            )
        elif part_type == "data":
            return DataPart(
                data=part_data["data"],
                metadata=part_data.get("metadata"),
            )
        elif part_type == "file":
            file_data = part_data["file"]
            file_content = FileContent(**file_data)
            return FilePart(
                file=file_content,
                metadata=part_data.get("metadata"),
            )
        else:
            raise TypeValidationError(f"Unsupported SDK part type: {part_type}")

    def _convert_artifact_to_sdk_dict(self, artifact) -> Dict[str, Any]:
        """Convert Restate Artifact to SDK dict format."""
        return {
            "name": artifact.name,
            "description": artifact.description,
            "parts": [self._convert_part_to_sdk_dict(part) for part in artifact.parts],
            "metadata": artifact.metadata,
            "index": artifact.index,
            "append": artifact.append,
            "lastChunk": artifact.lastChunk,
        }

    def _convert_artifact_from_sdk_dict(self, artifact_data: Dict[str, Any]):
        """Convert SDK dict to Restate Artifact."""
        from .models import Artifact

        return Artifact(
            name=artifact_data.get("name"),
            description=artifact_data.get("description"),
            parts=[self._convert_part_from_sdk_dict(part) for part in artifact_data["parts"]],
            metadata=artifact_data.get("metadata"),
            index=artifact_data.get("index", 0),
            append=artifact_data.get("append"),
            lastChunk=artifact_data.get("lastChunk"),
        )


# Global instances for easy usage
default_adapter = EnhancedA2ASDKAdapter(strict_validation=True)
lenient_adapter = EnhancedA2ASDKAdapter(strict_validation=False)