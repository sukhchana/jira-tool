import asyncio
from llm.vertexllm import VertexLLM
from loguru import logger

logger.add("test_vertexllm.log", rotation="500 MB")

async def main():
    try:
        llm = VertexLLM()
        print("Testing basic content generation...")
        response = await llm.generate_content("Hello, tell me a short joke")
        print(f"Response: {response}")
        
        print("\nTesting content generation with search...")
        response = await llm.generate_content_with_search("What are the latest developments in artificial intelligence?")
        print(f"Response with search: {response}")
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    print("Starting Vertex AI test...")
    asyncio.run(main()) 