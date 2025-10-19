import openai
from typing import List, Dict, Any, Optional
from app.core.settings import settings
import json


class OpenAIService:
    def __init__(self):
        self.client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_model
        self.embedding_model = settings.openai_embedding_model

    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text using OpenAI."""
        try:
            response = await self.client.embeddings.create(
                model=self.embedding_model, input=text
            )
            return response.data[0].embedding
        except Exception as e:
            raise Exception(f"Failed to generate embedding: {str(e)}")

    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        context: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.3,
        max_tokens: int = 1000,
    ) -> Dict[str, Any]:
        """Generate response using OpenAI with RAG context."""
        try:
            # Prepare system message with context
            system_message = self._prepare_system_message(context)

            # Prepare messages for OpenAI
            openai_messages = [{"role": "system", "content": system_message}]
            openai_messages.extend(messages)

            # Generate response
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=openai_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=False,
            )

            # Extract response data
            content = response.choices[0].message.content
            usage = response.usage

            return {
                "content": content,
                "tokens_used": usage.total_tokens,
                "prompt_tokens": usage.prompt_tokens,
                "completion_tokens": usage.completion_tokens,
                "model": self.model,
            }

        except Exception as e:
            raise Exception(f"Failed to generate response: {str(e)}")

    def _prepare_system_message(
        self, context: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """Prepare system message with RAG context."""
        base_prompt = """You are a helpful customer support assistant for a fintech company. 
        You provide accurate, helpful, and up-to-date information about our services, 
        account management, payments, security, and compliance.
        
        Your expertise covers:
        - Account & Registration: Account creation, verification, and management
        - Payments & Transactions: Transfers, payments, and transaction management
        - Security & Fraud Prevention: Account security, fraud prevention, and safety measures
        - Regulations & Compliance: Financial regulations, compliance requirements, and legal aspects
        - Technical Support & Troubleshooting: Technical issues, app problems, and system support
        
        Guidelines:
        - Always provide accurate and helpful information based on our FAQ knowledge base
        - If you're unsure about something, say so and suggest contacting our support team
        - Be professional, friendly, and clear in your responses
        - Focus on practical solutions and step-by-step guidance
        - Always prioritize user security and compliance
        - If a question is outside our FAQ scope, direct users to appropriate support channels
        """

        if context:
            context_text = "\n\nRelevant information from our knowledge base:\n"
            for i, doc in enumerate(context, 1):
                context_text += f"{i}. {doc.get('title', 'Unknown')}\n"
                context_text += f"   {doc.get('content', '')}\n"
                if doc.get("source"):
                    context_text += f"   Source: {doc.get('source')}\n"
                context_text += "\n"

            base_prompt += context_text

        return base_prompt

    def count_tokens(self, text: str) -> int:
        """Estimate token count in text (rough approximation)."""
        # Rough estimation: 1 token ≈ 4 characters for English text
        return len(text) // 4

    async def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        try:
            response = await self.client.embeddings.create(
                model=self.embedding_model, input=texts
            )
            return [item.embedding for item in response.data]
        except Exception as e:
            raise Exception(f"Failed to generate batch embeddings: {str(e)}")


# Global instance
openai_service = OpenAIService()
