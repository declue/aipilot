#!/usr/bin/env python
"""
CLI application for testing LLM functionality.
This module provides a command-line interface to test the LLM module's functionality.
"""

import argparse
import asyncio
from typing import Optional

from application.config.config_manager import ConfigManager
from application.llm.llm_agent import LLMAgent
from application.llm.mcp.mcp_manager import MCPManager
from application.llm.mcp.mcp_tool_manager import MCPToolManager
from application.util.logger import setup_logger

# Set up logger
logger = setup_logger("cli_app")


def init_llm_agent() -> LLMAgent:
    """
    Initialize the LLM agent with necessary components.
    
    Returns:
        LLMAgent: Initialized LLM agent
    """
    # Initialize ConfigManager
    config_manager = ConfigManager()
    
    # Initialize MCPManager
    mcp_manager = MCPManager(config_manager)
    
    # Initialize MCPToolManager
    mcp_tool_manager = MCPToolManager(mcp_manager, config_manager)
    
    # Initialize LLMAgent
    llm_agent = LLMAgent(config_manager, mcp_tool_manager)
    
    return llm_agent


async def chat_mode(llm_agent: LLMAgent) -> None:
    """
    Start an interactive chat session with the LLM agent.
    
    Args:
        llm_agent: The LLM agent to interact with
    """
    print("Starting chat mode. Type 'exit' or 'quit' to end the session.")
    print("Type 'clear' to clear the conversation history.")
    
    while True:
        try:
            # Get user input
            user_input = input("\nYou: ")
            
            # Check for exit commands
            if user_input.lower() in ["exit", "quit"]:
                print("Exiting chat mode.")
                break
            
            # Check for clear command
            if user_input.lower() == "clear":
                llm_agent.clear_conversation()
                print("Conversation history cleared.")
                continue
            
            # Generate response
            print("\nAssistant: ", end="", flush=True)
            
            # Define callback for streaming
            def streaming_callback(chunk: str) -> None:
                print(chunk, end="", flush=True)
            
            # Generate streaming response
            await llm_agent.generate_response_streaming(user_input, streaming_callback)
            print()  # Add a newline after the response
            
        except KeyboardInterrupt:
            print("\nExiting chat mode.")
            break
        except Exception as e:
            logger.error(f"Error in chat mode: {e}")
            print(f"\nError: {e}")


async def single_query_mode(llm_agent: LLMAgent, query: str) -> None:
    """
    Process a single query and exit.
    
    Args:
        llm_agent: The LLM agent to interact with
        query: The query to process
    """
    try:
        print(f"Processing query: {query}")
        print("\nAssistant: ", end="", flush=True)
        
        # Define callback for streaming
        def streaming_callback(chunk: str) -> None:
            print(chunk, end="", flush=True)
        
        # Generate streaming response
        await llm_agent.generate_response_streaming(query, streaming_callback)
        print()  # Add a newline after the response
        
    except Exception as e:
        logger.error(f"Error in single query mode: {e}")
        print(f"\nError: {e}")


async def main(query: Optional[str] = None) -> None:
    """
    Main entry point for the CLI application.
    
    Args:
        query: Optional query to process in single query mode
    """
    # Initialize LLM agent
    llm_agent = init_llm_agent()
    
    if query:
        # Single query mode
        await single_query_mode(llm_agent, query)
    else:
        # Interactive chat mode
        await chat_mode(llm_agent)


if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="CLI for testing LLM functionality")
    parser.add_argument("--query", "-q", type=str, help="Single query to process")
    args = parser.parse_args()
    
    # Run the main function
    asyncio.run(main(args.query))
