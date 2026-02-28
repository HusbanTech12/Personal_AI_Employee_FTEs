#!/usr/bin/env python3
"""
Autonomy Loop Agent (Ralph Wiggum Loop) - Gold+ Tier AI Employee

Enables autonomous multi-step task execution with self-recovery capabilities.

Loop Pattern:
    while goal_not_complete:
        plan()      # Generate/adjust plan
        execute()   # Run current step
        validate()  # Check step success
        recover()   # Handle failures
        retry()     # Retry with adjustments

Capabilities:
- Self-retry with configurable policies
- Dependency handling (sequential/parallel)
- Step continuation from saved state
- Partial completion recovery
- Exponential/linear/fixed backoff
- State persistence for crash recovery

Usage:
    python autonomy_loop_agent.py

Stop:
    Press Ctrl+C - state is preserved for continuation
"""

import os
import sys
import json
import logging
import time
import re
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, field, asdict
from enum import Enum
import copy

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("AutonomyLoopAgent")


class StepStatus(Enum):
    """Status of an execution step."""
    PENDING = "pending"
    READY = "ready"
    EXECUTING = "executing"
    VALIDATING = "validating"
    COMPLETE = "complete"
    FAILED = "failed"
    RECOVERING = "recovering"
    RETRYING = "retrying"
    SKIPPED = "skipped"
    BLOCKED = "blocked"


class RecoveryStrategy(Enum):
    """Recovery strategies for failed steps."""
    RETRY = "retry"
    ALTERNATIVE = "alternative"
    SKIP = "skip"
    PARTIAL = "partial"
    ESCALATE = "escalate"


@dataclass
class RetryPolicy:
    """Retry configuration for a step."""
    max_attempts: int = 3
    backoff: str = "exponential"  # fixed, exponential, linear
    base_delay: float = 5.0
    max_delay: float = 300.0
    timeout: float = 300.0
    
    def get_delay(self, attempt: int) -> float:
        """Calculate delay for retry attempt."""
        if self.backoff == "fixed":
            return self.base_delay
        elif self.backoff == "linear":
            return min(self.base_delay * attempt, self.max_delay)
        elif self.backoff == "exponential":
            return min(self.base_delay * (2 ** (attempt - 1)), self.max_delay)
        return self.base_delay


@dataclass
class StepDefinition:
    """Definition of an execution step."""
    step_id: str
    name: str
    action: str
    dependencies: List[str] = field(default_factory=list)
    inputs: List[Dict] = field(default_factory=list)
    outputs: List[Dict] = field(default_factory=list)
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)
    validation: Dict = field(default_factory=dict)
    optional: bool = False
    parallel_group: Optional[str] = None


@dataclass
class StepState:
    """Runtime state of a step."""
    step_id: str
    status: StepStatus = StepStatus.PENDING
    attempts: int = 0
    outputs: Dict = field(default_factory=dict)
    error: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    recovery: Optional[Dict] = field(default_factory=dict)


@dataclass
class ExecutionState:
    """Complete execution state for persistence."""
    goal: str
    status: str = "planning"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    current_step: Optional[str] = None
    steps: Dict[str, StepState] = field(default_factory=dict)
    variables: Dict = field(default_factory=dict)
    recovery_history: List[Dict] = field(default_factory=list)
    metrics: Dict = field(default_factory=dict)


class AutonomyLoopAgent:
    """
    Autonomy Loop Agent - Ralph Wiggum Loop implementation.
    
    Executes multi-step tasks with self-recovery capabilities.
    """
    
    def __init__(self, needs_action_dir: Path, logs_dir: Path, state_dir: Optional[Path] = None):
        self.needs_action_dir = needs_action_dir
        self.logs_dir = logs_dir
        self.state_dir = state_dir or (logs_dir / "autonomy_states")
        
        self.state_dir.mkdir(parents=True, exist_ok=True)
        
        self.current_execution: Optional[ExecutionState] = None
        self.processed_tasks: set = set()
        
        # Skill/action handlers
        self.action_handlers: Dict[str, callable] = {}
        self._register_default_handlers()
    
    def _register_default_handlers(self):
        """Register default action handlers."""
        self.action_handlers = {
            'noop': self._action_noop,
            'log': self._action_log,
            'set_variable': self._action_set_variable,
            'get_variable': self._action_get_variable,
            'wait': self._action_wait,
            'condition': self._action_condition,
        }
    
    def load_execution_state(self, state_file: Path) -> Optional[ExecutionState]:
        """Load execution state from file."""
        try:
            with open(state_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Convert dicts back to dataclasses
            steps = {}
            for step_id, step_data in data.get('steps', {}).items():
                step_state = StepState(**step_data)
                step_state.status = StepStatus(step_state.status)
                steps[step_id] = step_state
            
            state = ExecutionState(
                goal=data.get('goal', ''),
                status=data.get('status', 'planning'),
                created_at=data.get('created_at'),
                updated_at=data.get('updated_at'),
                current_step=data.get('current_step'),
                steps=steps,
                variables=data.get('variables', {}),
                recovery_history=data.get('recovery_history', []),
                metrics=data.get('metrics', {})
            )
            
            logger.info(f"Loaded execution state: {state.goal[:50]}...")
            return state
            
        except Exception as e:
            logger.error(f"Failed to load state: {e}")
            return None
    
    def save_execution_state(self, state: ExecutionState):
        """Save execution state to file."""
        state.updated_at = datetime.now().isoformat()
        
        # Create state file name from goal
        safe_goal = re.sub(r'[^\w\s-]', '', state.goal[:30]).strip().replace(' ', '_')
        state_file = self.state_dir / f"state_{safe_goal}.json"
        
        try:
            # Convert to serializable dict
            data = {
                'goal': state.goal,
                'status': state.status,
                'created_at': state.created_at,
                'updated_at': state.updated_at,
                'current_step': state.current_step,
                'steps': {k: asdict(v) for k, v in state.steps.items()},
                'variables': state.variables,
                'recovery_history': state.recovery_history,
                'metrics': state.metrics
            }
            
            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            
            logger.debug(f"Saved execution state: {state_file.name}")
            
        except Exception as e:
            logger.error(f"Failed to save state: {e}")
    
    def read_task(self, file_path: Path) -> Tuple[str, Dict]:
        """Read task file and extract frontmatter + content."""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        frontmatter = {}
        body = content
        
        frontmatter_match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
        if frontmatter_match:
            fm_text = frontmatter_match.group(1)
            for line in fm_text.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    frontmatter[key.strip()] = value.strip()
            body = content[frontmatter_match.end():]
        
        return body, frontmatter
    
    def parse_steps(self, content: str, frontmatter: Dict) -> List[StepDefinition]:
        """Parse execution steps from task content."""
        steps = []
        
        # Check for explicit step definitions in content
        step_pattern = r'-\s*step_id:\s*(\w+)\s*\n\s*name:\s*([^\n]+)\s*\n\s*action:\s*([^\n]+)'
        
        matches = re.findall(step_pattern, content)
        
        for match in matches:
            step_id, name, action = match
            
            # Parse dependencies
            deps_match = re.search(r'step_id:\s*' + re.escape(step_id) + r'[^\n]*\n(?:\s*[^\n]*\n)*?\s*dependencies:\s*\[([^\]]*)\]', content)
            dependencies = []
            if deps_match:
                deps_str = deps_match.group(1)
                dependencies = [d.strip() for d in deps_str.split(',') if d.strip()]
            
            # Parse retry policy
            retry_match = re.search(r'step_id:\s*' + re.escape(step_id) + r'[^\n]*\n(?:\s*[^\n]*\n)*?\s*retry_policy:\s*\n\s*max_attempts:\s*(\d+)', content)
            retry_policy = RetryPolicy()
            if retry_match:
                retry_policy.max_attempts = int(retry_match.group(1))
            
            steps.append(StepDefinition(
                step_id=step_id,
                name=name.strip(),
                action=action.strip(),
                dependencies=dependencies,
                retry_policy=retry_policy
            ))
        
        # If no explicit steps, create default plan from content
        if not steps:
            steps = self._generate_default_steps(frontmatter, content)
        
        return steps
    
    def _generate_default_steps(self, frontmatter: Dict, content: str) -> List[StepDefinition]:
        """Generate default execution steps from task content."""
        steps = []
        
        # Step 1: Analyze/Plan
        steps.append(StepDefinition(
            step_id="step_1_analyze",
            name="Analyze task requirements",
            action="log",
            retry_policy=RetryPolicy(max_attempts=2)
        ))
        
        # Step 2: Execute main action
        skill = frontmatter.get('skill', 'task_processor')
        steps.append(StepDefinition(
            step_id="step_2_execute",
            name=f"Execute {skill} action",
            action=skill,
            dependencies=["step_1_analyze"],
            retry_policy=RetryPolicy(max_attempts=3, backoff="exponential")
        ))
        
        # Step 3: Validate
        steps.append(StepDefinition(
            step_id="step_3_validate",
            name="Validate completion",
            action="condition",
            dependencies=["step_2_execute"],
            retry_policy=RetryPolicy(max_attempts=2)
        ))
        
        return steps
    
    def initialize_execution(self, goal: str, steps: List[StepDefinition]) -> ExecutionState:
        """Initialize new execution state."""
        state = ExecutionState(goal=goal)
        
        for step in steps:
            state.steps[step.step_id] = StepState(step_id=step.step_id)
        
        state.metrics = {
            'total_steps': len(steps),
            'completed_steps': 0,
            'failed_steps': 0,
            'retry_count': 0,
            'recovery_count': 0,
            'start_time': datetime.now().isoformat()
        }
        
        logger.info(f"Initialized execution: {goal}")
        logger.info(f"Total steps: {len(steps)}")
        
        return state
    
    def plan(self, state: ExecutionState, steps: List[StepDefinition]) -> List[str]:
        """
        PLAN phase: Determine which steps are ready to execute.
        
        Returns list of step IDs ready for execution.
        """
        ready_steps = []
        
        for step in steps:
            step_state = state.steps.get(step.step_id)
            if not step_state:
                continue
            
            # Skip completed or blocked steps
            if step_state.status in [StepStatus.COMPLETE, StepStatus.SKIPPED, StepStatus.BLOCKED]:
                continue
            
            # Check dependencies
            deps_satisfied = all(
                state.steps.get(dep_id, StepState(dep_id)).status == StepStatus.COMPLETE
                for dep_id in step.dependencies
            )
            
            if deps_satisfied:
                step_state.status = StepStatus.READY
                ready_steps.append(step.step_id)
        
        # Sort by parallel groups
        parallel_groups: Dict[str, List[str]] = {}
        sequential = []
        
        for step in steps:
            if step.step_id in ready_steps:
                if step.parallel_group:
                    if step.parallel_group not in parallel_groups:
                        parallel_groups[step.parallel_group] = []
                    parallel_groups[step.parallel_group].append(step.step_id)
                else:
                    sequential.append(step.step_id)
        
        # Return steps in execution order
        result = sequential
        for group_steps in parallel_groups.values():
            result.extend(group_steps)
        
        logger.debug(f"Planning complete: {len(result)} steps ready")
        
        return result
    
    def execute(self, state: ExecutionState, step: StepDefinition) -> Tuple[bool, Dict]:
        """
        EXECUTE phase: Run the step action.
        
        Returns (success, outputs).
        """
        step_state = state.steps[step.step_id]
        step_state.status = StepStatus.EXECUTING
        step_state.started_at = datetime.now().isoformat()
        step_state.attempts += 1
        
        state.current_step = step.step_id
        state.metrics['retry_count'] = state.metrics.get('retry_count', 0) + 1
        
        logger.info(f"Executing: {step.name} (attempt {step_state.attempts})")
        
        try:
            # Gather inputs from dependencies
            inputs = self._gather_inputs(state, step)
            
            # Get action handler
            handler = self.action_handlers.get(step.action)
            
            if not handler:
                # Try to execute as skill
                handler = self._get_skill_handler(step.action)
            
            if handler:
                outputs = handler(step, inputs, state.variables)
                step_state.outputs = outputs
                self.save_execution_state(state)
                return True, outputs
            else:
                # Simulate execution for unknown actions
                logger.warning(f"Unknown action: {step.action} - simulating")
                time.sleep(1)  # Simulate work
                step_state.outputs = {'simulated': True, 'action': step.action}
                return True, step_state.outputs
                
        except Exception as e:
            logger.error(f"Execution failed: {e}")
            step_state.error = str(e)
            return False, {'error': str(e)}
    
    def _gather_inputs(self, state: ExecutionState, step: StepDefinition) -> Dict:
        """Gather inputs from completed dependency steps."""
        inputs = {}
        
        for input_def in step.inputs:
            from_step = input_def.get('from')
            variable = input_def.get('variable')
            
            if from_step and from_step in state.steps:
                dep_outputs = state.steps[from_step].outputs
                if variable and variable in dep_outputs:
                    inputs[variable] = dep_outputs[variable]
                else:
                    inputs.update(dep_outputs)
        
        return inputs
    
    def _get_skill_handler(self, skill_name: str) -> Optional[callable]:
        """Get handler for a skill action."""
        # Placeholder for skill integration
        # In production, this would load and call actual skill agents
        def skill_handler(step, inputs, variables):
            logger.info(f"Executing skill: {skill_name}")
            return {'skill': skill_name, 'executed': True}
        
        return skill_handler
    
    def validate(self, state: ExecutionState, step: StepDefinition, outputs: Dict) -> bool:
        """
        VALIDATE phase: Check if step completed successfully.
        """
        step_state = state.steps[step.step_id]
        step_state.status = StepStatus.VALIDATING
        
        logger.debug(f"Validating: {step.name}")
        
        # Check for explicit error
        if step_state.error:
            return False
        
        # Check validation conditions
        validation = step.validation
        
        if not validation:
            # Default: success if no error and has outputs
            return not step_state.error
        
        # Custom validation
        validation_type = validation.get('type', 'output_exists')
        
        if validation_type == 'output_exists':
            required_output = validation.get('output')
            if required_output:
                return required_output in outputs
            return bool(outputs)
        
        elif validation_type == 'custom':
            condition = validation.get('condition', '')
            # Evaluate condition against outputs
            # In production, use safe expression evaluation
            return True  # Simplified
        
        elif validation_type == 'api_check':
            # Would call API to verify
            return True
        
        return True
    
    def recover(self, state: ExecutionState, step: StepDefinition, error: str) -> RecoveryStrategy:
        """
        RECOVER phase: Determine recovery strategy for failed step.
        """
        step_state = state.steps[step.step_id]
        
        logger.info(f"Recovering from failure: {step.name} - {error}")
        
        # Check retry policy
        retry_policy = step.retry_policy
        
        if step_state.attempts < retry_policy.max_attempts:
            # Can retry
            strategy = RecoveryStrategy.RETRY
            
            # Record recovery
            recovery_record = {
                'step': step.step_id,
                'attempt': step_state.attempts,
                'error': error,
                'strategy': strategy.value,
                'timestamp': datetime.now().isoformat()
            }
            state.recovery_history.append(recovery_record)
            step_state.recovery = recovery_record
            state.metrics['recovery_count'] = state.metrics.get('recovery_count', 0) + 1
            
            logger.info(f"Recovery strategy: RETRY (attempt {step_state.attempts}/{retry_policy.max_attempts})")
            return strategy
        
        # Max retries exceeded
        if step.optional:
            logger.info(f"Recovery strategy: SKIP (optional step)")
            return RecoveryStrategy.SKIP
        
        # Check for alternative approaches
        if self._has_alternative(step):
            logger.info(f"Recovery strategy: ALTERNATIVE")
            return RecoveryStrategy.ALTERNATIVE
        
        # Cannot recover
        logger.error(f"Recovery strategy: ESCALATE (cannot recover)")
        return RecoveryStrategy.ESCALATE
    
    def _has_alternative(self, step: StepDefinition) -> bool:
        """Check if alternative approach exists for step."""
        # In production, check for alternative actions
        return False
    
    def retry(self, state: ExecutionState, step: StepDefinition, strategy: RecoveryStrategy) -> bool:
        """
        RETRY phase: Prepare and execute retry.
        """
        step_state = state.steps[step.step_id]
        retry_policy = step.retry_policy
        
        if strategy == RecoveryStrategy.RETRY:
            # Calculate backoff delay
            delay = retry_policy.get_delay(step_state.attempts)
            logger.info(f"Retrying after {delay}s backoff")
            time.sleep(delay)
            
            step_state.status = StepStatus.RETRYING
            step_state.error = None
            return True
        
        elif strategy == RecoveryStrategy.SKIP:
            step_state.status = StepStatus.SKIPPED
            step_state.completed_at = datetime.now().isoformat()
            return False
        
        elif strategy == RecoveryStrategy.ESCALATE:
            step_state.status = StepStatus.BLOCKED
            return False
        
        return False
    
    def run_loop(self, state: ExecutionState, steps: List[StepDefinition]) -> bool:
        """
        Execute the Ralph Wiggum Loop until goal is complete.
        """
        max_iterations = 100  # Safety limit
        iteration = 0
        
        logger.info("=" * 60)
        logger.info("Starting Ralph Wiggum Loop")
        logger.info(f"Goal: {state.goal}")
        logger.info("=" * 60)
        
        while iteration < max_iterations:
            iteration += 1
            
            # Check if complete
            if self._is_goal_complete(state, steps):
                state.status = "complete"
                state.metrics['end_time'] = datetime.now().isoformat()
                self.save_execution_state(state)
                logger.info("=" * 60)
                logger.info("Goal Complete!")
                logger.info(f"Total iterations: {iteration}")
                logger.info(f"Completed steps: {state.metrics.get('completed_steps', 0)}/{len(steps)}")
                logger.info("=" * 60)
                return True
            
            # Check if blocked
            if self._is_blocked(state, steps):
                state.status = "blocked"
                self.save_execution_state(state)
                logger.warning("Execution blocked - requires intervention")
                return False
            
            # PLAN
            ready_steps = self.plan(state, steps)
            
            if not ready_steps:
                # No steps ready - check if waiting or stuck
                time.sleep(2)
                continue
            
            # EXECUTE + VALIDATE + RECOVER + RETRY
            for step_id in ready_steps:
                step = next((s for s in steps if s.step_id == step_id), None)
                if not step:
                    continue
                
                # Execute
                success, outputs = self.execute(state, step)
                
                # Validate
                if success:
                    valid = self.validate(state, step, outputs)
                    
                    if valid:
                        state.steps[step_id].status = StepStatus.COMPLETE
                        state.steps[step_id].completed_at = datetime.now().isoformat()
                        state.metrics['completed_steps'] = state.metrics.get('completed_steps', 0) + 1
                        logger.info(f"✓ Complete: {step.name}")
                    else:
                        # Validation failed - treat as execution failure
                        success = False
                        outputs = {'error': 'Validation failed'}
                
                # Recover/Retry if failed
                if not success:
                    error = state.steps[step_id].error or outputs.get('error', 'Unknown error')
                    strategy = self.recover(state, step, error)
                    
                    if self.retry(state, step, strategy):
                        # Will retry on next iteration
                        pass
                    else:
                        # Skip or blocked
                        if strategy == RecoveryStrategy.ESCALATE:
                            state.metrics['failed_steps'] = state.metrics.get('failed_steps', 0) + 1
            
            # Save state after each iteration
            self.save_execution_state(state)
            
            # Progress report
            completed = state.metrics.get('completed_steps', 0)
            total = len(steps)
            progress = (completed / total) * 100 if total > 0 else 0
            logger.info(f"Progress: [{completed}/{total}] {progress:.1f}%")
        
        logger.error(f"Max iterations ({max_iterations}) exceeded")
        state.status = "failed"
        self.save_execution_state(state)
        return False
    
    def _is_goal_complete(self, state: ExecutionState, steps: List[StepDefinition]) -> bool:
        """Check if goal is complete."""
        required_steps = [s for s in steps if not s.optional]
        completed = sum(
            1 for s in required_steps
            if state.steps.get(s.step_id, StepState(s.step_id)).status == StepStatus.COMPLETE
        )
        return completed == len(required_steps)
    
    def _is_blocked(self, state: ExecutionState, steps: List[StepDefinition]) -> bool:
        """Check if execution is blocked."""
        # Check for any blocked required steps
        for step in steps:
            if step.optional:
                continue
            step_state = state.steps.get(step.step_id)
            if step_state and step_state.status == StepStatus.BLOCKED:
                return True
        
        # Check for unsatisfiable dependencies
        for step in steps:
            if step.optional:
                continue
            step_state = state.steps.get(step.step_id)
            if step_state and step_state.status == StepStatus.PENDING:
                # Check if any dependency is blocked
                for dep_id in step.dependencies:
                    dep_state = state.steps.get(dep_id)
                    if dep_state and dep_state.status == StepStatus.BLOCKED:
                        return True
        
        return False
    
    # Default action handlers
    
    def _action_noop(self, step, inputs, variables) -> Dict:
        """No operation - for testing."""
        return {'status': 'noop'}
    
    def _action_log(self, step, inputs, variables) -> Dict:
        """Log message."""
        message = inputs.get('message', step.name)
        logger.info(f"[{step.step_id}] {message}")
        return {'logged': message}
    
    def _action_set_variable(self, step, inputs, variables) -> Dict:
        """Set a variable."""
        name = inputs.get('name', 'unknown')
        value = inputs.get('value')
        variables[name] = value
        return {'variable': name, 'value': value}
    
    def _action_get_variable(self, step, inputs, variables) -> Dict:
        """Get a variable."""
        name = inputs.get('name')
        return {'value': variables.get(name)}
    
    def _action_wait(self, step, inputs, variables) -> Dict:
        """Wait for specified duration."""
        seconds = float(inputs.get('seconds', 1))
        logger.info(f"Waiting {seconds}s...")
        time.sleep(seconds)
        return {'waited': seconds}
    
    def _action_condition(self, step, inputs, variables) -> Dict:
        """Evaluate a condition."""
        condition = inputs.get('condition', 'true')
        # Simplified - in production use safe expression evaluation
        result = True
        return {'condition': condition, 'result': result}
    
    def process_task(self, task_file: Path) -> bool:
        """Process a single task through the autonomy loop."""
        task_name = task_file.name
        logger.info(f"Processing task: {task_name}")
        
        # Read task
        content, frontmatter = self.read_task(task_file)
        
        # Check for existing state (crash recovery)
        safe_goal = re.sub(r'[^\w\s-]', '', frontmatter.get('title', task_name)[:30]).strip().replace(' ', '_')
        state_file = self.state_dir / f"state_{safe_goal}.json"
        
        if state_file.exists():
            logger.info(f"Found existing state - resuming")
            state = self.load_execution_state(state_file)
            if state and state.status not in ['complete', 'blocked', 'failed']:
                # Resume existing execution
                steps = self.parse_steps(content, frontmatter)
                return self.run_loop(state, steps)
        
        # New execution
        goal = frontmatter.get('title', task_name)
        steps = self.parse_steps(content, frontmatter)
        
        state = self.initialize_execution(goal, steps)
        self.save_execution_state(state)
        
        # Run the loop
        success = self.run_loop(state, steps)
        
        # Update task file
        self._update_task_file(task_file, state)
        
        self.processed_tasks.add(task_name)
        
        return success
    
    def _update_task_file(self, task_file: Path, state: ExecutionState):
        """Update task file with execution results."""
        try:
            with open(task_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Add execution summary
            summary = f"""
---

## Execution Summary

**Status:** {'✅ Complete' if state.status == 'complete' else '❌ ' + state.status.title()}
**Completed:** {timestamp}
**Steps:** {state.metrics.get('completed_steps', 0)}/{state.metrics.get('total_steps', 0)}
**Retries:** {state.metrics.get('retry_count', 0)}
**Recoveries:** {state.metrics.get('recovery_count', 0)}

### Step Results

"""
            for step_id, step_state in state.steps.items():
                status_icon = '✓' if step_state.status == StepStatus.COMPLETE else '✗'
                summary += f"- [{status_icon}] {step_id}: {step_state.status.value}\n"
            
            if state.status == 'complete':
                content = re.sub(r'(status:\s*)[^\n]+', r'\1done', content, flags=re.MULTILINE)
                if 'completed:' not in content:
                    content = re.sub(r'(status:\s*done)', f'\\1\ncompleted: {timestamp}', content)
            
            new_content = content + summary
            
            with open(task_file, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            logger.info(f"Task file updated: {task_file.name}")
            
        except Exception as e:
            logger.error(f"Failed to update task file: {e}")
    
    def scan_for_tasks(self) -> List[Path]:
        """Scan Needs_Action for autonomy loop tasks."""
        tasks = []
        
        if not self.needs_action_dir.exists():
            return tasks
        
        for file_path in self.needs_action_dir.iterdir():
            if file_path.is_file() and file_path.suffix.lower() == '.md':
                if file_path.name in self.processed_tasks:
                    continue
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check for autonomy loop indicator
                is_autonomy = (
                    'skill: autonomy_loop' in content.lower() or
                    'autonomy' in content.lower() or
                    'multi-step' in content.lower() or
                    'workflow' in content.lower()
                )
                
                if is_autonomy:
                    tasks.append(file_path)
        
        return tasks
    
    def run(self):
        """Main autonomy loop agent loop."""
        logger.info("=" * 60)
        logger.info("Autonomy Loop Agent (Ralph Wiggum Loop) started")
        logger.info(f"State directory: {self.state_dir}")
        logger.info("=" * 60)
        logger.info("")
        logger.info("Loop: plan → execute → validate → recover → retry")
        logger.info("")
        
        while True:
            try:
                tasks = self.scan_for_tasks()
                
                if tasks:
                    logger.info(f"Found {len(tasks)} autonomy task(s)")
                    
                    for task_file in tasks:
                        self.process_task(task_file)
                    
                    logger.info("Waiting for more tasks...")
                
                # Check for incomplete states (crash recovery)
                self._check_incomplete_states()
                
                time.sleep(5)
                
            except KeyboardInterrupt:
                logger.info("")
                logger.info("Autonomy Loop Agent stopping...")
                logger.info("State preserved - will resume on restart")
                break
            except Exception as e:
                logger.error(f"Error in autonomy loop: {e}")
                time.sleep(5)
    
    def _check_incomplete_states(self):
        """Check for and resume incomplete execution states."""
        for state_file in self.state_dir.glob("state_*.json"):
            state = self.load_execution_state(state_file)
            if state and state.status in ['planning', 'executing', 'validating', 'recovering', 'retrying']:
                logger.info(f"Found incomplete state: {state_file.name}")
                # Could resume here automatically
                # For now, just log


if __name__ == "__main__":
    BASE_DIR = Path(__file__).parent.parent
    VAULT_PATH = BASE_DIR / "notes"
    agent = AutonomyLoopAgent(
        needs_action_dir=VAULT_PATH / "Needs_Action",
        logs_dir=BASE_DIR / "Logs"
    )
    agent.run()
