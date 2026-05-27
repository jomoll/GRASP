#Structure documentation https://github.com/THUDM/AgentBench/blob/main/docs/Extension_en.md
from typing import Callable, Dict, List, Any
from src.server.task import Task, Session
from src.typings import TaskOutput, SampleStatus, AgentOutputStatus
from .utils import *
from .eval import eval
import time
import json
import importlib

_TASK_CURRENT_TIME = "2023-11-13T10:15:00+00:00"


def _build_task_prompt(api_base: str, functions: list, context: str, question: str) -> str:
    return json.dumps({
        "phase": "task_execution",
        "task": {
            "description": question,
            "context": (context + "\n" if context else "") + f"Current time: {_TASK_CURRENT_TIME}",
        },
        "behavioral_skills": "",     # populated by SkillAwareAgent at inference time
        "api": {
            "base_url": api_base,
            "functions": functions,
        },
        "response_format": {
            "type": "api_action",
            "options": [
                "GET url?param_name1=param_value1&param_name2=param_value2",
                "POST url\n{json_payload}",
                "FINISH([answer1, answer2, ...])",
            ],
            "rules": [
                "Respond with exactly ONE action per turn — no other text",
                "FINISH list must be JSON-loadable (strings inside quotes)",
            ],
        },
    }, indent=2)

class MedAgentBench(Task):
    def __init__(self, **configs):
        super().__init__(**configs)
        self.data_file = configs.pop("data_file")
        with open(self.data_file, 'r') as f:
            self.data = json.load(f)
        
        self.func_file = configs.pop("func_file")
        with open(self.func_file, 'r') as f:
            self.funcs = json.load(f)
        
        self.max_round = configs.pop("max_round", 5)

        self.fhir_api_base = configs.pop("fhir_api_base")
        if verify_fhir_server(self.fhir_api_base) is False:
            print('FHIR server connection error! Please check FHIR server status and fhir_api_base in configs/tasks/medagentbench.yaml')
        try:
            module_name = 'src.server.tasks.medagentbench.refsol'
            refsol = importlib.import_module(module_name)
        except:
            print('Make sure to download the refsol.py and save as `src/server/tasks/medagentbench/refsol.py`')
            exit()

    def get_indices(self) -> List[Any]:
        return list(range(len(self.data))) #[20]#[10*i for i in range(10)]

    async def start_sample(self, index, session: Session):
        print(f"task start {index}")
        case = self.data[index]
        session.inject({"role": "user", "content": _build_task_prompt(
            api_base=self.fhir_api_base,
            functions=self.funcs,
            context=case['context'],
            question=case['instruction'],
        )})
        try:
            for round in range(self.max_round):
                #time.sleep(5.0) Add for rate limit

                res = (await session.action())
                if res.status == AgentOutputStatus.AGENT_CONTEXT_LIMIT:
                    return TaskOutput(
                    status=SampleStatus.AGENT_CONTEXT_LIMIT,
                    history=session.history
                )
                r = res.content.strip().replace('```tool_code', '').replace('```', '').strip() #Remove separator for Gemini2.0Flash

                if r.startswith('GET'):
                    url = r[3:].strip() + '&_format=json'
                    #print(f'GET {url}')
                    get_res = send_get_request(url)
                    if "data" in get_res:
                        session.inject({"role": "user", "content": f"Here is the response from the GET request:\n{get_res['data']}. Please call FINISH if you have got answers for all the questions and finished all the requested tasks"})
                    else:
                        session.inject({"role": "user", "content": f"Error in sending the GET request: {get_res['error']}"})

                elif r.startswith('POST'):
                    try:
                        payload = json.loads('\n'.join(r.split('\n')[1:]))
                    except Exception as e:
                        session.inject({"role": "user", "content": "Invalid POST request"})
                    else:
                        session.inject({"role": "user", "content": "POST request accepted and executed successfully. Please call FINISH if you have got answers for all the questions and finished all the requested tasks"})
                elif r.startswith('FINISH('):
                    return TaskOutput(
                        status=SampleStatus.COMPLETED,
                        result=r[len('FINISH('):-1], #Trim to a list
                        history=session.history
                    )
                else:
                    return TaskOutput(
                        status=SampleStatus.AGENT_INVALID_ACTION,
                        history=session.history
                    )
                
        except Exception as e:
            return TaskOutput(
                status=SampleStatus.TASK_ERROR,
                result={"error": str(e)},
                history=session.history
            )
        
        return TaskOutput(
            status=SampleStatus.TASK_LIMIT_REACHED,
            history=session.history
        )

    def calculate_overall(self, results: List[TaskOutput]) -> Dict[str, Any]:
        total_task = len(results)
        assert len(self.get_indices()) == total_task
        correct_count = 0
        for i in range(total_task):
            if getattr(results[i], "result") is not None:
                index = results[i].index
                if eval(self.data[index], results[i], self.fhir_api_base) is True:
                    correct_count += 1
                    results[i].status += 'Correct'
                else:
                    results[i].status += 'Incorrect'

        return {'success rate': correct_count/total_task, 'raw_results': results}