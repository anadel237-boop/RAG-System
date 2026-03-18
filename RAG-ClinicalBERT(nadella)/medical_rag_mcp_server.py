#!/usr/bin/env python3
"""
Medical RAG MCP Server
Model Context Protocol server for medical RAG system
"""

import asyncio
import json
import os
from typing import Any, Dict, List, Optional
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import (
    CallToolRequest,
    ListToolsRequest,
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
)

# Import our RAG system
from medical_rag_system import MedicalRAGSystem

class MedicalRAGMCPServer:
    """MCP Server for Medical RAG System"""
    
    def __init__(self):
        self.server = Server("medical-rag-system")
        self.rag_system = None
        self.setup_handlers()
    
    def setup_handlers(self):
        """Setup MCP server handlers"""
        
        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            """List available medical RAG tools"""
            return [
                Tool(
                    name="medical_query",
                    description="Query medical cases using RAG",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Medical query or question"
                            },
                            "case_id": {
                                "type": "string",
                                "description": "Specific case ID to focus on",
                                "default": None
                            }
                        },
                        "required": ["query"]
                    }
                ),
                Tool(
                    name="patient_query",
                    description="Query specific patient case",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "patient_id": {
                                "type": "string",
                                "description": "Patient case ID (e.g., case_0001_mimic.txt)"
                            },
                            "symptoms": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of symptoms or conditions"
                            }
                        },
                        "required": ["patient_id", "symptoms"]
                    }
                ),
                Tool(
                    name="medical_search",
                    description="Search for similar medical cases",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query for medical cases"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of results",
                                "default": 5
                            }
                        },
                        "required": ["query"]
                    }
                ),
                Tool(
                    name="medical_stats",
                    description="Get medical RAG system statistics",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                ),
                Tool(
                    name="medical_embedding",
                    description="Get vector embedding for medical text",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "text": {
                                "type": "string",
                                "description": "Text to get embedding for"
                            }
                        },
                        "required": ["text"]
                    }
                )
            ]
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            """Handle tool calls"""
            
            if not self.rag_system:
                return [TextContent(
                    type="text",
                    text="❌ Medical RAG system not initialized. Please check your Neon connection."
                )]
            
            try:
                if name == "medical_query":
                    return await self.handle_medical_query(arguments)
                elif name == "patient_query":
                    return await self.handle_patient_query(arguments)
                elif name == "medical_search":
                    return await self.handle_medical_search(arguments)
                elif name == "medical_stats":
                    return await self.handle_medical_stats(arguments)
                elif name == "medical_embedding":
                    return await self.handle_medical_embedding(arguments)
                else:
                    return [TextContent(
                        type="text",
                        text=f"❌ Unknown tool: {name}"
                    )]
            except Exception as e:
                return [TextContent(
                    type="text",
                    text=f"❌ Error executing {name}: {str(e)}"
                )]
    
    async def handle_medical_query(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle medical query"""
        query = arguments.get("query", "")
        case_id = arguments.get("case_id")
        
        if not query:
            return [TextContent(
                type="text",
                text="❌ No query provided"
            )]
        
        # Query medical cases
        result = self.rag_system.query_medical_cases(query, case_id)
        
        if not result.relevant_cases:
            return [TextContent(
                type="text",
                text="❌ No relevant medical cases found"
            )]
        
        result_text = f"🔍 **Medical Query Results**\n\n"
        result_text += f"**Query:** {result.query}\n"
        result_text += f"**Confidence:** {result.confidence:.2f}\n"
        result_text += f"**Processing Time:** {result.processing_time:.2f}s\n\n"
        result_text += f"**Medical Analysis:**\n{result.answer}\n\n"
        result_text += f"**Sources:** {', '.join(result.sources)}\n\n"
        result_text += f"**Relevant Cases Found:** {len(result.relevant_cases)}"
        
        return [TextContent(type="text", text=result_text)]
    
    async def handle_patient_query(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle patient-specific query"""
        patient_id = arguments.get("patient_id", "")
        symptoms = arguments.get("symptoms", [])
        
        if not patient_id:
            return [TextContent(
                type="text",
                text="❌ No patient ID provided"
            )]
        
        if not symptoms:
            return [TextContent(
                type="text",
                text="❌ No symptoms provided"
            )]
        
        # Create query from symptoms
        query = f"Patient {patient_id} with symptoms: {', '.join(symptoms)}"
        
        # Query with specific patient focus
        result = self.rag_system.query_medical_cases(query, patient_id)
        
        result_text = f"👤 **Patient-Specific Analysis**\n\n"
        result_text += f"**Patient ID:** {patient_id}\n"
        result_text += f"**Symptoms:** {', '.join(symptoms)}\n"
        result_text += f"**Confidence:** {result.confidence:.2f}\n"
        result_text += f"**Processing Time:** {result.processing_time:.2f}s\n\n"
        result_text += f"**Medical Analysis:**\n{result.answer}\n\n"
        result_text += f"**Sources:** {', '.join(result.sources)}"
        
        return [TextContent(type="text", text=result_text)]
    
    async def handle_medical_search(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle medical case search"""
        query = arguments.get("query", "")
        limit = arguments.get("limit", 5)
        
        if not query:
            return [TextContent(
                type="text",
                text="❌ No search query provided"
            )]
        
        # Get embedding for search
        embedding = self.rag_system.get_embedding(query)
        if not embedding:
            return [TextContent(
                type="text",
                text="❌ Failed to get embedding for search"
            )]
        
        # Search similar cases
        similar_cases = self.rag_system.neon_db.search_similar_cases(embedding, limit=limit)
        
        if not similar_cases:
            return [TextContent(
                type="text",
                text="❌ No similar medical cases found"
            )]
        
        result_text = f"🔍 **Medical Case Search Results**\n\n"
        result_text += f"**Search Query:** {query}\n"
        result_text += f"**Results Found:** {len(similar_cases)}\n\n"
        
        for i, case in enumerate(similar_cases, 1):
            result_text += f"{i}. **{case['case_id']}** (Similarity: {case['similarity']:.3f})\n"
            result_text += f"   Content: {case['content'][:200]}...\n\n"
        
        return [TextContent(type="text", text=result_text)]
    
    async def handle_medical_stats(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle medical statistics"""
        stats = self.rag_system.neon_db.get_system_stats()
        
        if not stats:
            return [TextContent(
                type="text",
                text="❌ Failed to get medical statistics"
            )]
        
        result_text = f"📊 **Medical RAG System Statistics**\n\n"
        result_text += f"**Total Medical Cases:** {stats.get('total_cases', 0)}\n"
        result_text += f"**Total Queries:** {stats.get('total_queries', 0)}\n"
        result_text += f"**Average Confidence:** {stats.get('average_confidence', 0):.2f}\n\n"
        result_text += f"**System Status:** ✅ Operational\n"
        result_text += f"**Neon Database:** ✅ Connected\n"
        result_text += f"**OpenAI Integration:** ✅ Available"
        
        return [TextContent(type="text", text=result_text)]
    
    async def handle_medical_embedding(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle embedding generation"""
        text = arguments.get("text", "")
        
        if not text:
            return [TextContent(
                type="text",
                text="❌ No text provided for embedding"
            )]
        
        embedding = self.rag_system.get_embedding(text)
        if not embedding:
            return [TextContent(
                type="text",
                text="❌ Failed to generate embedding"
            )]
        
        return [TextContent(
            type="text",
            text=f"🔢 **Vector Embedding Generated**\n\n"
                 f"**Text:** {text}\n"
                 f"**Embedding Dimension:** {len(embedding)}\n"
                 f"**First 5 values:** {embedding[:5]}\n"
                 f"**Last 5 values:** {embedding[-5:]}"
        )]
    
    async def initialize_rag_system(self):
        """Initialize the medical RAG system"""
        try:
            # Load environment
            from dotenv import load_dotenv
            load_dotenv()
            
            neon_connection = os.getenv('NEON_CONNECTION_STRING')
            openai_key = os.getenv('OPENAI_API_KEY')
            
            if not neon_connection or not openai_key:
                print("❌ Missing environment variables. Please check your .env file.")
                return False
            
            # Initialize RAG system
            self.rag_system = MedicalRAGSystem(neon_connection, openai_key)
            
            # Connect to database
            if not self.rag_system.neon_db.connect():
                print("❌ Failed to connect to Neon database")
                return False
            
            print("✅ Medical RAG MCP Server initialized")
            return True
            
        except Exception as e:
            print(f"❌ Failed to initialize RAG system: {e}")
            return False
    
    async def run(self):
        """Run the MCP server"""
        # Initialize RAG system
        await self.initialize_rag_system()
        
        # Run the server
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="medical-rag-system",
                    server_version="1.0.0",
                ),
            )

async def main():
    """Main function"""
    server = MedicalRAGMCPServer()
    await server.run()

if __name__ == "__main__":
    asyncio.run(main())





