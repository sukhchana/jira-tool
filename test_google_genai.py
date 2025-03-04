import asyncio
import os
from llm.genaillm import GenAILLM
from loguru import logger

# Configure logging
logger.add("test_google_genai.log", rotation="500 MB")

async def main():
    """Test the GenAILLM class with various scenarios"""
    try:
        print("Initializing GenAI LLM...")
        llm = GenAILLM()
        
        # Test 1: Basic content generation
        print("\n=== Test 1: Basic content generation ===")
        response = await llm.generate_content(
            "Tell me a short joke about programming",
            temperature=0.7
        )
        print(f"Response: {response}")
        
        # Test 2: Content generation with Google Search grounding
        print("\n=== Test 2: Content generation with Google Search grounding ===")
        search_prompt = "When is the next total solar eclipse in the United States?"
        print(f"Prompt: {search_prompt}")
        response = await llm.generate_content_with_search(
            search_prompt,
            temperature=0.0
        )
        print(f"Response with search: {response}")
        
        # Test 3: Current events query with Google Search grounding
        print("\n=== Test 3: Current events query with Google Search grounding ===")
        news_prompt = "What are the latest major global news headlines today? Summarize the top 5."
        print(f"Prompt: {news_prompt}")
        response = await llm.generate_content_with_search(
            news_prompt,
            temperature=0.2
        )
        print(f"Response with news search: {response}")
        
        # Success message
        print("\nAll tests completed successfully!")
        
    except Exception as e:
        logger.error(f"Error during testing: {str(e)}")
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    print("Starting Google GenAI test...")
    print("Make sure you have set these environment variables:")
    print("- GCP_PROJECT_ID")
    print("- VERTEX_LOCATION (optional, defaults to us-central1)")
    print("- VERTEX_MODEL_VERSION (optional, defaults to gemini-2.0-flash)")
    print("\nRunning tests...")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as e:
        print(f"Test failed with error: {str(e)}") 