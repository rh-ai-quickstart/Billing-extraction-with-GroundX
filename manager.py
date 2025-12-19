import typing

from groundx import (
    WorkflowPrompt,
    WorkflowPromptGroup,
    WorkflowResponse,
    WorkflowStepConfig,
    WorkflowStep,
    WorkflowSteps,
)
from groundx.extract import PromptManager

from prompts.extract_statement import (
    prompt_statement_extract_request,
    prompt_statement_extract_task,
)
from prompts.qa_statement import prompt_statement_qa
from prompts.reconcile_statement import prompt_statement_reconcile


class ExtractPromptManager(PromptManager):
    def __init__(
        self,
        **data: typing.Any,
    ) -> None:
        super().__init__(**data)

        if not self.is_init:
            raise Exception(
                f"[{self.default_workflow_id}] [{self.default_file_name}.yaml] is not init"
            )

    def init_prompts(
        self,
        file_name: typing.Optional[str] = None,
        workflow_id: typing.Optional[str] = None,
    ) -> WorkflowResponse:
        return self.gx_client.workflows.create(
            chunk_strategy="element",
            name="account default",
            steps=self.workflow_steps(
                file_name=self.file_name(file_name),
                workflow_id=self.workflow_id(workflow_id),
            ),
            extract=self.workflow_extract_dict(
                file_name=self.file_name(file_name),
                workflow_id=self.workflow_id(workflow_id),
            ),
        )

    def prompt_statement_extract(
        self,
        file_name: typing.Optional[str] = None,
        workflow_id: typing.Optional[str] = None,
    ) -> WorkflowStepConfig:
        return WorkflowStepConfig(
            field="sect-sum",
            includes={
                "pageImages": True,
            },
            prompt=WorkflowPromptGroup(
                request=WorkflowPrompt(
                    prompt=prompt_statement_extract_request(
                        self.group_field_prompts(
                            "statement", file_name=file_name, workflow_id=workflow_id
                        ),
                    ),
                    role="assistant",
                ),
                task=WorkflowPrompt(
                    prompt=prompt_statement_extract_task(
                        self.group_descriptions(
                            "statement", file_name=file_name, workflow_id=workflow_id
                        ),
                    ),
                    role="developer",
                ),
            ),
        )

    def prompt_statement_reconcile(
        self,
        num_fields: int,
        field_desc: str,
        file_name: typing.Optional[str] = None,
        workflow_id: typing.Optional[str] = None,
    ) -> str:
        return prompt_statement_reconcile(
            num_fields=num_fields,
            field_desc=field_desc,
        )

    def prompt_statement_qa(
        self,
        statement_fields: str,
        statement_field_keys: typing.List[str],
        file_name: typing.Optional[str] = None,
        workflow_id: typing.Optional[str] = None,
    ) -> str:
        return prompt_statement_qa(
            statement_fields,
            statement_field_keys,
            self.group_field_prompts(
                "statement", file_name=file_name, workflow_id=workflow_id
            ),
        )

    def update_prompts(
        self,
        workflow_id: str,
        file_name: typing.Optional[str] = None,
    ) -> WorkflowResponse:
        return self.gx_client.workflows.update(
            id=workflow_id,
            chunk_strategy="element",
            name="account default",
            steps=self.workflow_steps(
                file_name=self.file_name(file_name), workflow_id=workflow_id
            ),
            extract=self.workflow_extract_dict(
                file_name=self.file_name(file_name), workflow_id=workflow_id
            ),
        )

    def workflow_steps(
        self,
        file_name: typing.Optional[str] = None,
        workflow_id: typing.Optional[str] = None,
    ) -> WorkflowSteps:
        statement_step = self.prompt_statement_extract(
            file_name=file_name, workflow_id=workflow_id
        )

        return WorkflowSteps(
            chunk_instruct=WorkflowStep(
                figure=statement_step,
                paragraph=statement_step,
                json_=None,
                table_figure=statement_step,
            ),
            chunk_summary=None,
            doc_keys=None,
            doc_summary=None,
            sect_instruct=None,
            sect_summary=None,
        )
