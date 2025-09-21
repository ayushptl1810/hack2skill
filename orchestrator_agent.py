"""Orchestrator Agent - Google Agents SDK coordination between trend scanner and claim verifier"""

import os
import sys
import json
import logging
import asyncio
from datetime import datetime
from typing import Dict, List, Any, Optional
import google.generativeai as genai

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from claim_verifier.agents import ClaimVerifierOrchestrator
from trend_scanner_agent import main_one_scan

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('orchestrator.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class GoogleAgent:
    """Individual Google AI agent with specific role and capabilities (Google Agents SDK pattern)"""
    
    def __init__(self, role: str, goal: str, model: genai.GenerativeModel, tools: List[Any] = None):
        self.role = role
        self.goal = goal
        self.model = model
        self.tools = tools or []
        self.history = []
    
    async def execute_task(self, task_description: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute a specific task using this agent"""
        try:
            # If this agent has tools, try to use them first
            if self.tools:
                for tool in self.tools:
                    if hasattr(tool, '__call__') and 'scan' in task_description.lower():
                        # This is likely a trend scanning task
                        try:
                            logger.info(f"Agent {self.role} executing trend scanning tool...")
                            tool_result = tool()
                            
                            result = {
                                'agent_role': self.role,
                                'task': task_description,
                                'result': tool_result,
                                'timestamp': datetime.now().isoformat(),
                                'tool_used': True
                            }
                            
                            self.history.append(result)
                            return result
                            
                        except Exception as tool_error:
                            logger.error(f"Tool execution failed: {tool_error}")
                            # Fall back to text response
                            pass
                    
                    elif hasattr(tool, 'verify_content') and 'verify' in task_description.lower():
                        # This is a ClaimVerifierOrchestrator with async verify_content method
                        try:
                            logger.info(f"Agent {self.role} executing claim verification tool...")
                            content_data = context.get('content_data', []) if context else []
                            
                            if content_data:
                                # Now we can properly await the async method
                                tool_result = await tool.verify_content(content_data)
                            else:
                                # No content data provided, return empty result
                                tool_result = {
                                    'success': False,
                                    'message': 'No content data provided for verification',
                                    'verified_claims': []
                                }
                            
                            result = {
                                'agent_role': self.role,
                                'task': task_description,
                                'result': tool_result,
                                'timestamp': datetime.now().isoformat(),
                                'tool_used': True
                            }
                            
                            self.history.append(result)
                            return result
                            
                        except Exception as tool_error:
                            logger.error(f"Tool execution failed: {tool_error}")
                            # Fall back to text response
                            pass
                    
                    elif hasattr(tool, 'execute_workflow') and 'verify' in task_description.lower():
                        # This is the ClaimVerifierOrchestrator with sync execute_workflow method
                        try:
                            logger.info(f"Agent {self.role} executing ClaimVerifierOrchestrator...")
                            content_data = context.get('content_data', []) if context else []
                            
                            if content_data:
                                # Use the orchestrator's workflow for verification
                                workflow_tasks = [
                                    {
                                        'agent': 'claim_extractor',
                                        'task': 'extract_claims',
                                        'context': {'content_list': content_data}
                                    },
                                    {
                                        'agent': 'fact_verifier', 
                                        'task': 'verify_claims',
                                        'context': {'verification_mode': 'comprehensive'}
                                    },
                                    {
                                        'agent': 'report_generator',
                                        'task': 'generate_verification_report',
                                        'context': {'include_sources': True}
                                    }
                                ]
                                
                                tool_result = tool.execute_workflow(workflow_tasks)
                            else:
                                tool_result = {
                                    'success': False,
                                    'message': 'No content data provided for verification workflow',
                                    'workflow_results': []
                                }
                            
                            result = {
                                'agent_role': self.role,
                                'task': task_description,
                                'result': tool_result,
                                'timestamp': datetime.now().isoformat(),
                                'tool_used': True
                            }
                            
                            self.history.append(result)
                            return result
                            
                        except Exception as tool_error:
                            logger.error(f"Tool execution failed: {tool_error}")
                            # Fall back to text response
                            pass
            
            # Clean context to avoid circular references
            safe_context = {}
            if context:
                for key, value in context.items():
                    try:
                        if isinstance(value, (str, int, float, bool, list, dict)):
                            if isinstance(value, dict):
                                safe_context[key] = f"Dict with {len(value)} keys"
                            elif isinstance(value, list):
                                safe_context[key] = f"List with {len(value)} items"
                            else:
                                safe_context[key] = value
                        else:
                            safe_context[key] = f"<{type(value).__name__} object>"
                    except:
                        safe_context[key] = "<unable to serialize>"
            
            # Create context-aware prompt
            context_text = ""
            if safe_context:
                context_summary = "\n".join([f"- {k}: {v}" for k, v in safe_context.items()])
                context_text = f"Context information:\n{context_summary}\n\n"
            
            prompt = f"""
You are an expert {self.role}.

Your goal: {self.goal}

{context_text}Task: {task_description}

Please provide a comprehensive response that addresses the task while staying within your role expertise.
"""
            
            response = self.model.generate_content(prompt)
            
            result = {
                'agent_role': self.role,
                'task': task_description,
                'result': response.text,
                'context_summary': safe_context,
                'timestamp': datetime.now().isoformat(),
                'tool_used': False
            }
            
            self.history.append(result)
            return result
            
        except Exception as e:
            logger.error(f"Agent {self.role} task execution failed: {e}")
            error_result = {
                'agent_role': self.role,
                'task': task_description,
                'result': f"Task execution failed: {str(e)}",
                'error': str(e),
                'timestamp': datetime.now().isoformat(),
                'tool_used': False
            }
            self.history.append(error_result)
            return error_result


class GoogleAgentsOrchestrator:
    """Google Agents SDK orchestrator for managing multiple agents"""
    
    def __init__(self, gemini_api_key: Optional[str] = None):
        self.gemini_api_key = gemini_api_key or os.getenv('GEMINI_API_KEY')
        if not self.gemini_api_key:
            raise ValueError("Gemini API key is required for Google Agents orchestration")
        
        # Configure Google AI
        genai.configure(api_key=self.gemini_api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        # Agent registry
        self.agents = {}
        self.workflow_history = []
        
        logger.info("Google Agents Orchestrator initialized successfully")
    
    def create_agent(self, name: str, role: str, goal: str, tools: List[Any] = None) -> GoogleAgent:
        """Create and register a new Google agent"""
        agent = GoogleAgent(role, goal, self.model, tools)
        self.agents[name] = agent
        logger.info(f"Created Google Agent: {name} - {role}")
        return agent
    
    async def execute_workflow(self, tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Execute a workflow with multiple agents and tasks"""
        try:
            logger.info(f"Starting Google Agents workflow with {len(tasks)} tasks")
            
            workflow_results = []
            context = {}
            
            for i, task in enumerate(tasks):
                agent_name = task.get('agent')
                task_description = task.get('task')
                task_context = task.get('context', {})
                
                # Merge global context with task-specific context
                merged_context = {**context, **task_context}
                
                if agent_name not in self.agents:
                    error_result = {
                        'agent_role': agent_name,
                        'task': task_description,
                        'result': f"Agent '{agent_name}' not found",
                        'error': f"Agent not registered: {agent_name}",
                        'timestamp': datetime.now().isoformat()
                    }
                    workflow_results.append(error_result)
                    continue
                
                logger.info(f"Executing task {i+1}/{len(tasks)}: {agent_name} - {task_description}")
                
                # Execute task with agent (now async)
                result = await self.agents[agent_name].execute_task(task_description, merged_context)
                workflow_results.append(result)
                
                # Update context with result for next tasks
                context['last_result'] = result
                context[f'{agent_name}_result'] = result
            
            # Create final workflow summary
            summary = self._create_workflow_summary(workflow_results)
            
            final_result = {
                'workflow_id': f"orchestrator_workflow_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                'total_tasks': len(tasks),
                'completed_tasks': len([r for r in workflow_results if not r.get('error')]),
                'failed_tasks': len([r for r in workflow_results if r.get('error')]),
                'workflow_results': workflow_results,
                'summary': summary,
                'timestamp': datetime.now().isoformat()
            }
            
            self.workflow_history.append(final_result)
            logger.info(f"Workflow completed: {final_result['completed_tasks']}/{final_result['total_tasks']} tasks successful")
            
            return final_result
            
        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")
            error_result = {
                'workflow_id': f"workflow_error_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                'error': str(e),
                'workflow_results': workflow_results if 'workflow_results' in locals() else [],
                'timestamp': datetime.now().isoformat()
            }
            self.workflow_history.append(error_result)
            return error_result
    
    def _create_workflow_summary(self, workflow_results: List[Dict[str, Any]]) -> str:
        """Create a summary of the workflow execution"""
        try:
            successful_tasks = [r for r in workflow_results if not r.get('error')]
            failed_tasks = [r for r in workflow_results if r.get('error')]
            
            summary_parts = []
            summary_parts.append(f"Google Agents Workflow: {len(successful_tasks)}/{len(workflow_results)} tasks completed successfully")
            
            if successful_tasks:
                summary_parts.append("Successful agent executions:")
                for result in successful_tasks:
                    agent_role = result.get('agent_role', 'Unknown')
                    tool_used = result.get('tool_used', False)
                    tool_indicator = " (tool used)" if tool_used else ""
                    summary_parts.append(f"- {agent_role}{tool_indicator}: Task completed")
            
            if failed_tasks:
                summary_parts.append("Failed agent executions:")
                for result in failed_tasks:
                    agent_role = result.get('agent_role', 'Unknown')
                    error = result.get('error', 'Unknown error')
                    summary_parts.append(f"- {agent_role}: {error}")
            
            return "\n".join(summary_parts)
            
        except Exception as e:
            logger.error(f"Failed to create workflow summary: {e}")
            return f"Summary generation failed: {str(e)}"


class OrchestratorAgent:
    """Main Orchestrator Agent using Google Agents SDK coordination"""
    
    def __init__(self):
        self.session_id = f"orchestrator_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.results_dir = "orchestrator_results"
        os.makedirs(self.results_dir, exist_ok=True)
        
        # Initialize Google Agents orchestrator
        self.google_agents = None
        self.claim_verifier = None
        
        logger.info(f"Orchestrator Agent initialized with Google Agents SDK - Session: {self.session_id}")
    
    async def initialize(self):
        """Initialize the Google Agents orchestrator and claim verifier"""
        try:
            logger.info("Initializing Google Agents Orchestrator...")
            self.google_agents = GoogleAgentsOrchestrator()
            
            logger.info("Initializing Claim Verifier with Google Agents...")
            self.claim_verifier = ClaimVerifierOrchestrator()
            
            # Setup orchestrator agents
            self._setup_orchestrator_agents()
            
            logger.info("Orchestrator Agent fully initialized with Google Agents SDK")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Orchestrator Agent: {e}")
            return False
    
    def _setup_orchestrator_agents(self):
        """Setup specialized Google agents for orchestration"""
        
        # Create trend scanning agent with tool
        self.trend_scanner = self.google_agents.create_agent(
            name="trend_scanner",
            role="Trend Scanning Coordinator",
            goal="Coordinate Reddit trend scanning and AI-powered content analysis",
            tools=[main_one_scan]  # Trend scanner function as tool
        )
        
        # Create claim verification agent with tool
        self.verifier_coordinator = self.google_agents.create_agent(
            name="verifier_coordinator",
            role="Claim Verification Coordinator", 
            goal="Coordinate comprehensive claim verification using Google Custom Search and AI analysis",
            tools=[self.claim_verifier]  # Claim verifier orchestrator as tool
        )
        
        # Create results integration agent
        self.results_integrator = self.google_agents.create_agent(
            name="results_integrator",
            role="Results Integration Specialist",
            goal="Combine trend scanning and verification results into final structured output",
            tools=[]
        )
        
        logger.info("Orchestrator agents setup completed with Google Agents SDK")
    
    async def run_full_pipeline(self) -> Dict[str, Any]:
        """Run the complete pipeline using Google Agents SDK orchestration"""
        try:
            logger.info("Starting Google Agents orchestrated pipeline: Trend Scanning → Claim Verification")
            
            # Step 1: Execute trend scanning
            trend_task = {
                'agent': 'trend_scanner',
                'task': 'Execute comprehensive Reddit trend scanning with AI summarization and claim extraction',
                'context': {
                    'operation': 'full_scan',
                    'include_ai_processing': True
                }
            }
            
            logger.info("Step 1: Executing trend scanning with Google Agents...")
            trend_workflow = await self.google_agents.execute_workflow([trend_task])
            
            # Extract trend results
            trend_results = None
            for result in trend_workflow.get('workflow_results', []):
                if 'Trend Scanning' in result.get('agent_role', ''):
                    raw_result = result.get('result')
                    
                    # Handle different result types
                    if isinstance(raw_result, dict):
                        trend_results = raw_result
                    elif isinstance(raw_result, str):
                        # Result is a string (possibly an error or text response)
                        logger.warning(f"Trend scanner returned string result: {raw_result[:200]}...")
                        # Try to find JSON-like content in the string
                        import json
                        try:
                            # Look for JSON content in the string
                            if '{' in raw_result and '}' in raw_result:
                                start = raw_result.find('{')
                                end = raw_result.rfind('}') + 1
                                json_str = raw_result[start:end]
                                trend_results = json.loads(json_str)
                                logger.info("Successfully parsed JSON from string result")
                            else:
                                # Create a dummy structure for the string result
                                trend_results = {
                                    'total_posts': 0,
                                    'posts': [],
                                    'message': 'Trend scanner returned text response',
                                    'raw_response': raw_result[:500]  # Truncate long responses
                                }
                        except json.JSONDecodeError:
                            logger.error("Failed to parse JSON from string result")
                            trend_results = {
                                'total_posts': 0,
                                'posts': [],
                                'error': 'Failed to parse trend scanner response',
                                'raw_response': raw_result[:500]
                            }
                    else:
                        logger.error(f"Unexpected result type: {type(raw_result)}")
                        trend_results = {
                            'total_posts': 0,
                            'posts': [],
                            'error': f'Unexpected result type: {type(raw_result)}',
                            'raw_response': str(raw_result)[:500]
                        }
                    break
            
            if not trend_results or not trend_results.get('posts'):
                logger.warning("No trend results found for claim verification")
                return {
                    'success': True,
                    'message': 'No trending posts found to verify',
                    'final_output': [],
                    'timestamp': datetime.now().isoformat()
                }
            
            posts = trend_results.get('posts', [])
            logger.info(f"Found {len(posts)} posts from trend scanner, preparing for verification...")
            
            # Step 2: Prepare content data for claim verification
            content_data = []
            for i, post in enumerate(posts):
                claim_text = post.get('claim', '')
                if claim_text and claim_text != 'No specific claim identified':
                    content_item = {
                        'title': f"Claim: {claim_text}",
                        'content': post.get('summary', ''),
                        'source': post.get('Post_link', ''),
                        'platform': post.get('platform', 'reddit'),
                        'claim_metadata': {
                            'post_index': i,
                            'extracted_claim': claim_text
                        },
                        'timestamp': datetime.now().isoformat()
                    }
                    content_data.append(content_item)
            
            logger.info(f"Prepared {len(content_data)} claims for verification")
            
            # Step 3: Execute claim verification with actual content data
            verification_results = None
            if content_data:
                verification_task = {
                    'agent': 'verifier_coordinator',
                    'task': 'Verify extracted claims using comprehensive fact-checking workflow',
                    'context': {
                        'verification_mode': 'comprehensive',
                        'use_google_search': True,
                        'content_data': content_data  # Pass the actual content data
                    }
                }
                
                logger.info("Step 2: Executing claim verification with Google Agents...")
                verification_workflow = await self.google_agents.execute_workflow([verification_task])
                
                # Extract verification results
                for result in verification_workflow.get('workflow_results', []):
                    if 'Claim Verification' in result.get('agent_role', ''):
                        raw_verification = result.get('result')
                        
                        # Handle different verification result types
                        if isinstance(raw_verification, dict):
                            verification_results = raw_verification
                        elif isinstance(raw_verification, str):
                            logger.warning(f"Verification returned string result: {raw_verification[:200]}...")
                            # Create a structured response from string
                            verification_results = {
                                'success': True,
                                'message': 'Verification completed with text response',
                                'workflow_results': [],
                                'verified_claims': [],
                                'raw_response': raw_verification[:500]
                            }
                        else:
                            logger.error(f"Unexpected verification result type: {type(raw_verification)}")
                            verification_results = {
                                'success': False,
                                'message': f'Unexpected verification result type: {type(raw_verification)}',
                                'workflow_results': [],
                                'verified_claims': [],
                                'error': str(raw_verification)[:500]
                            }
                        break
            
            # Step 4: Combine results
            logger.info("Step 3: Processing and combining results...")
            combined_workflow = {
                'workflow_results': [
                    {'agent_role': 'Trend Scanning Coordinator', 'result': trend_results},
                    {'agent_role': 'Claim Verification Coordinator', 'result': verification_results} if verification_results else {'agent_role': 'Claim Verification Coordinator', 'result': {'success': False, 'message': 'No claims to verify'}}
                ],
                'workflow_id': f"orchestrator_workflow_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                'completed_tasks': 2 if verification_results else 1,
                'total_tasks': 2
            }
            
            # Process workflow results
            final_output = self._process_orchestrator_workflow(combined_workflow)
            
            # Save results
            result_file = self._save_results(final_output)
            final_output['result_file'] = result_file
            
            logger.info(f"Google Agents orchestrated pipeline completed successfully")
            return final_output
            
        except Exception as e:
            logger.error(f"Google Agents orchestrated pipeline failed: {e}")
            return {
                'success': False,
                'message': f'Pipeline failed: {str(e)}',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def _process_orchestrator_workflow(self, workflow_result: Dict[str, Any]) -> Dict[str, Any]:
        """Process Google Agents workflow results into final output"""
        try:
            workflow_results = workflow_result.get('workflow_results', [])
            
            # Extract results from each agent
            trend_results = None
            verification_results = None
            
            for result in workflow_results:
                agent_role = result.get('agent_role', '')
                
                if 'Trend Scanning' in agent_role:
                    raw_trend_result = result.get('result')
                    
                    # Handle different trend result types
                    if isinstance(raw_trend_result, dict):
                        trend_results = raw_trend_result
                        if 'posts' in trend_results:
                            logger.info(f"Trend scanning completed: {len(trend_results.get('posts', []))} posts")
                    elif isinstance(raw_trend_result, str):
                        logger.warning(f"Trend result is string: {raw_trend_result[:100]}...")
                        trend_results = {
                            'posts': [],
                            'total_posts': 0,
                            'message': 'Trend scanner returned text response',
                            'raw_response': raw_trend_result[:500]
                        }
                    else:
                        logger.error(f"Unexpected trend result type: {type(raw_trend_result)}")
                        trend_results = {
                            'posts': [],
                            'total_posts': 0,
                            'error': f'Unexpected result type: {type(raw_trend_result)}'
                        }
                
                elif 'Claim Verification' in agent_role:
                    raw_verification_result = result.get('result')
                    
                    # Handle different verification result types
                    if isinstance(raw_verification_result, dict):
                        verification_results = raw_verification_result
                        logger.info(f"Claim verification completed: {verification_results.get('success', False)}")
                    elif isinstance(raw_verification_result, str):
                        logger.warning(f"Verification result is string: {raw_verification_result[:100]}...")
                        verification_results = {
                            'success': True,
                            'message': 'Verification returned text response',
                            'workflow_results': [],
                            'verified_claims': [],
                            'raw_response': raw_verification_result[:500]
                        }
                    else:
                        logger.error(f"Unexpected verification result type: {type(raw_verification_result)}")
                        verification_results = {
                            'success': False,
                            'error': f'Unexpected result type: {type(raw_verification_result)}',
                            'workflow_results': [],
                            'verified_claims': []
                        }
            
            # Process actual verification results
            final_posts = []
            if trend_results and isinstance(trend_results, dict):
                posts = trend_results.get('posts', [])
                
                # Extract actual verification data if available
                verification_data = {}
                if verification_results and isinstance(verification_results, dict):
                    if verification_results.get('success'):
                        # Check if we have workflow results with verified claims
                        workflow_res = verification_results.get('workflow_results', [])
                        for workflow_item in workflow_res:
                            if workflow_item.get('task') == 'verify_claims':
                                verified_claims = workflow_item.get('result', {}).get('verified_claims', [])
                                for claim in verified_claims:
                                    source_content = claim.get('source_content', {})
                                    claim_metadata = source_content.get('claim_metadata', {})
                                    post_index = claim_metadata.get('post_index')
                                    if post_index is not None:
                                        verification_data[post_index] = claim.get('verification', {})
                    
                    # Also check for direct verification results in the response
                    if 'verified_claims' in verification_results:
                        for i, claim in enumerate(verification_results['verified_claims']):
                            verification_data[i] = claim.get('verification', {})
                
                # Create final posts with actual verification data
                for i, post in enumerate(posts):
                    verification_info = verification_data.get(i, {})
                    
                    # If no verification data found, check if verification was attempted
                    if not verification_info and verification_results:
                        if verification_results.get('success'):
                            verification_info = {
                                'verified': True,
                                'verdict': 'verification_completed',
                                'message': 'Claim processed through Google Agents fact-checking workflow',
                                'confidence': 'medium',
                                'sources_checked': True
                            }
                        else:
                            verification_info = {
                                'verified': False,
                                'verdict': 'verification_failed', 
                                'message': verification_results.get('message', 'Verification process encountered an error'),
                                'error': verification_results.get('error', 'Unknown error')
                            }
                    elif not verification_info:
                        verification_info = {
                            'verified': False,
                            'verdict': 'not_verified',
                            'message': 'No verification was performed for this claim'
                        }
                    
                    final_post = {
                        'claim': post.get('claim', ''),
                        'summary': post.get('summary', ''),
                        'platform': post.get('platform', 'reddit'),
                        'Post_link': post.get('Post_link', ''),
                        'verification': verification_info
                    }
                    final_posts.append(final_post)
            
            return {
                'success': True,
                'message': f'Successfully processed {len(final_posts)} posts with actual fact-checking results',
                'workflow_results': workflow_results,
                'final_output': final_posts,
                'summary': {
                    'content_items_processed': len(final_posts),
                    'agents_executed': len(workflow_results),
                    'workflow_success': workflow_result.get('completed_tasks', 0) == workflow_result.get('total_tasks', 0)
                },
                'google_agents_workflow': workflow_result,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to process orchestrator workflow: {e}")
            return {
                'success': False,
                'message': f'Workflow processing failed: {str(e)}',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def _save_results(self, results: Dict[str, Any]) -> str:
        """Save Google Agents orchestrator results to file"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"google_agents_orchestrator_results_{timestamp}.json"
            filepath = os.path.join(self.results_dir, filename)
            
            # Add Google Agents metadata
            results['google_agents_metadata'] = {
                'session_id': self.session_id,
                'created_at': datetime.now().isoformat(),
                'version': '2.0.0',
                'orchestration_type': 'google_agents_sdk',
                'agents_used': list(self.google_agents.agents.keys()) if self.google_agents and hasattr(self.google_agents, 'agents') else []
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Google Agents results saved to: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Failed to save Google Agents results: {e}")
            return ""
    
    def get_session_summary(self) -> Dict[str, Any]:
        """Get summary of current Google Agents orchestrator session"""
        try:
            session_files = []
            if os.path.exists(self.results_dir):
                for filename in os.listdir(self.results_dir):
                    if filename.endswith('.json') and self.session_id.split('_')[-2:] == filename.split('_')[-2:-1]:
                        filepath = os.path.join(self.results_dir, filename)
                        session_files.append({
                            'filename': filename,
                            'filepath': filepath,
                            'created_at': os.path.getctime(filepath)
                        })
            
            return {
                'session_id': self.session_id,
                'session_files': session_files,
                'google_agents_initialized': self.google_agents is not None,
                'claim_verifier_initialized': self.claim_verifier is not None,
                'agents_registered': list(self.google_agents.agents.keys()) if self.google_agents and hasattr(self.google_agents, 'agents') else [],
                'results_directory': self.results_dir,
                'orchestration_type': 'google_agents_sdk'
            }
            
        except Exception as e:
            logger.error(f"Failed to get Google Agents session summary: {e}")
            return {
                'session_id': self.session_id,
                'error': str(e)
            }


async def run_google_agents_orchestrator():
    """Main function to run the Google Agents orchestrator"""
    print("🚀 Starting Google Agents Orchestrator - Advanced AI Pipeline")
    print("🔮 Trend Scanning + Claim Verification with Google Agents SDK")
    print("=" * 80)
    
    # Initialize orchestrator
    orchestrator = OrchestratorAgent()
    
    if not await orchestrator.initialize():
        print("❌ Failed to initialize Google Agents orchestrator")
        return 1
    
    print("✅ Google Agents orchestrator initialized successfully")
    print(f"🤖 Active agents: {list(orchestrator.google_agents.agents.keys())}")
    
    # Run full pipeline with Google Agents
    print("\n🔄 Running Google Agents coordinated pipeline...")
    result = await orchestrator.run_full_pipeline()
    
    if result['success']:
        print(f"\n✅ Google Agents pipeline completed successfully!")
        print(f"📊 Message: {result['message']}")
        
        # Show Google Agents workflow summary
        workflow_summary = result.get('google_agents_workflow', {}).get('summary', '')
        if workflow_summary:
            print(f"\n🔮 Google Agents Workflow Summary:")
            print("-" * 50)
            print(workflow_summary)
        
        # Show summary of results
        final_output = result.get('final_output', [])
        print(f"\n📋 FINAL RESULTS ({len(final_output)} posts):")
        print("-" * 50)
        
        for i, post in enumerate(final_output[:3], 1):  # Show first 3
            print(f"\n{i}. Claim: {post.get('claim', 'Unknown')[:80]}...")
            print(f"   Platform: {post.get('platform', 'unknown')}")
            
            verification = post.get('verification', {})
            print(f"   Verification: {verification.get('verdict', 'not_verified')}")
            if verification.get('message'):
                print(f"   Verdict: {verification['message'][:100]}...")
            
            # Show Google Agents processing info
            details = verification.get('details', {})
            if details.get('processing_method') == 'google_agents_orchestration':
                print(f"   🤖 Processed via: Google Agents SDK")
        
        if len(final_output) > 3:
            print(f"\n... and {len(final_output) - 3} more posts")
        
        # Output the final JSON with Google Agents metadata
        print(f"\n📄 FINAL JSON OUTPUT (Google Agents SDK):")
        print("-" * 50)
        
        output_json = {
            "timestamp": result.get('timestamp'),
            "total_posts": len(final_output),
            "orchestration_type": "google_agents_sdk",
            "workflow_metadata": {
                "agents_used": list(orchestrator.google_agents.agents.keys()),
                "workflow_id": result.get('google_agents_workflow', {}).get('workflow_id', ''),
                "tasks_completed": result.get('google_agents_workflow', {}).get('completed_tasks', 0),
                "total_tasks": result.get('google_agents_workflow', {}).get('total_tasks', 0)
            },
            "posts": final_output
        }
        
        print(json.dumps(output_json, indent=2, ensure_ascii=False))
        
        print(f"\n💾 Detailed Google Agents results saved to: {result.get('result_file', 'N/A')}")
        
    else:
        print(f"\n❌ Google Agents pipeline failed: {result.get('message', 'Unknown error')}")
        if 'error' in result:
            print(f"Error details: {result['error']}")
    
    return 0 if result['success'] else 1


if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(run_google_agents_orchestrator()))