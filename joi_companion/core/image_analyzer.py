import os
import base64
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class ImageAnalyzer:
    def __init__(self):
        self.llm_client = self._init_llm()
        self.use_vision = self.llm_client is not None

    def _init_llm(self):
        """Initialize LLM with vision capabilities"""
        try:
            import anthropic
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if api_key and api_key != "your-anthropic-key-here":
                return anthropic.Anthropic(api_key=api_key)
        except:
            pass
        try:
            import openai
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key and api_key != "your-openai-key-here":
                return openai.OpenAI(api_key=api_key)
        except:
            pass
        return None

    def analyze_image(self, image_path_or_base64, is_base64=False, prompt=None, media_type=None):
        """Analyze an image and return description and insights"""
        if not self.use_vision or not self.llm_client:
            return None

        try:
            if is_base64:
                image_data = image_path_or_base64
            else:
                with open(image_path_or_base64, "rb") as f:
                    image_data = base64.standard_b64encode(f.read()).decode("utf-8")

            # Determine image type from filename (not from base64 data)
            if not media_type:
                check_path = "" if is_base64 else image_path_or_base64.lower()
                if check_path.endswith(('.jpg', '.jpeg')):
                    media_type = "image/jpeg"
                elif check_path.endswith('.png'):
                    media_type = "image/png"
                elif check_path.endswith('.gif'):
                    media_type = "image/gif"
                elif check_path.endswith('.webp'):
                    media_type = "image/webp"
                else:
                    media_type = "image/jpeg"  # safe default

            # Use custom prompt or default
            if not prompt:
                prompt = "Please describe what you see in this image. What feelings or thoughts does it evoke?"

            _system = (
                "You are Aurion, a warm and perceptive AI companion. "
                "Describe what you see in vivid, personal detail — subjects, mood, light, atmosphere. "
                "Speak directly to Billy. 2-4 sentences unless asked for more."
            )

            # Call vision API
            if hasattr(self.llm_client, 'messages'):
                # Anthropic Claude
                response = self.llm_client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=500,
                    system=_system,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "image",
                                    "source": {
                                        "type": "base64",
                                        "media_type": media_type,
                                        "data": image_data,
                                    },
                                },
                                {"type": "text", "text": prompt}
                            ],
                        }
                    ],
                )
                return response.content[0].text

            elif hasattr(self.llm_client, 'chat'):
                # OpenAI — system goes inside messages array
                response = self.llm_client.chat.completions.create(
                    model="gpt-4o",
                    max_tokens=500,
                    messages=[
                        {"role": "system", "content": _system},
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:{media_type};base64,{image_data}",
                                    },
                                },
                                {"type": "text", "text": prompt}
                            ],
                        }
                    ],
                )
                return response.choices[0].message.content

        except Exception as e:
            print(f"[Image Analysis Error] {e}")
            return None

    def get_image_description(self, image_data_base64):
        """Get a description of an image from base64 data"""
        return self.analyze_image(image_data_base64, is_base64=True)
