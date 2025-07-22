"""
Core chatbot logic with bug fixes and improvements.
"""

import torch
import logging
from typing import List, Dict, Tuple, Optional

logger = logging.getLogger(__name__)

class MedicalChatbot:
    def __init__(self, model, tokenizer, device, df):
        self.model = model
        self.tokenizer = tokenizer
        self.device = device
        self.df = df
        self.emergency_symptoms = [
            "severe chest pain", "difficulty breathing", "unconscious", 
            "severe bleeding", "stroke symptoms", "heart attack symptoms",
            "severe headache", "loss of consciousness", "severe abdominal pain"
        ]
        
    def predict_disease(self, symptoms: str, top_n: int = 3) -> List[Dict]:
        """
        Predict diseases based on symptoms with improved error handling.
        
        Args:
            symptoms: String of symptoms separated by commas
            top_n: Number of top predictions to return
            
        Returns:
            List of disease predictions with confidence scores
        """
        try:
            # First, try direct dataset matching
            dataset_matches = self._get_dataset_matches(symptoms)
            if dataset_matches:
                return dataset_matches[:top_n]
            
            # If no direct matches, use model prediction
            model_predictions = self._get_model_predictions(symptoms, top_n)
            return model_predictions
            
        except Exception as e:
            logger.error(f"Error in predict_disease: {e}")
            return [{"disease": "Unable to predict", "confidence": 0.0, "source": "error"}]
    
    def _get_dataset_matches(self, symptoms: str) -> List[Dict]:
        """Get direct matches from the dataset."""
        input_symptoms_list = [s.strip().lower() for s in symptoms.split(',')]
        dataset_matches = []
        
        for _, row in self.df.iterrows():
            disease_name = row['disease']
            disease_symptoms = [s.strip().lower() for s in row['symptoms'].split(',')]
            
            # Check if ALL input symptoms are in this disease's symptoms
            all_symptoms_present = all(
                any(input_symptom in disease_symptom for disease_symptom in disease_symptoms)
                for input_symptom in input_symptoms_list
            )
            
            if all_symptoms_present:
                # Calculate confidence based on symptom overlap
                matched_count = sum(
                    1 for input_symptom in input_symptoms_list
                    if any(input_symptom in disease_symptom for disease_symptom in disease_symptoms)
                )
                confidence = matched_count / len(disease_symptoms) if disease_symptoms else 0
                
                dataset_matches.append({
                    'disease': disease_name,
                    'confidence': confidence,
                    'source': 'dataset'
                })
        
        # Remove duplicates and sort by confidence
        unique_diseases = {}
        for match in dataset_matches:
            disease_key = match['disease'].lower()
            if disease_key not in unique_diseases or match['confidence'] > unique_diseases[disease_key]['confidence']:
                unique_diseases[disease_key] = match
        
        return sorted(unique_diseases.values(), key=lambda x: x['confidence'], reverse=True)
    
    def _get_model_predictions(self, symptoms: str, top_n: int) -> List[Dict]:
        """Get predictions from the trained model."""
        try:
            input_text = f"Symptoms: {symptoms} | Disease:"
            input_ids = self.tokenizer.encode(input_text, return_tensors='pt').to(self.device)
            
            # Generate predictions with proper attention mask
            attention_mask = torch.ones_like(input_ids)
            
            with torch.no_grad():
                output = self.model.generate(
                    input_ids,
                    attention_mask=attention_mask,
                    max_length=50,
                    num_return_sequences=min(top_n * 2, 10),
                    do_sample=True,
                    top_k=50,
                    top_p=0.95,
                    temperature=0.7,
                    repetition_penalty=1.2,
                    pad_token_id=self.tokenizer.eos_token_id
                )
            
            predictions = []
            for i, sequence in enumerate(output):
                decoded_output = self.tokenizer.decode(sequence, skip_special_tokens=True)
                
                if "|" in decoded_output:
                    parts = decoded_output.split("|")
                    if len(parts) > 1:
                        disease = parts[1].strip()
                        if disease.startswith("Disease:"):
                            disease = disease[8:].strip()
                        
                        # Simple confidence scoring based on generation order
                        confidence = max(0.1, 1.0 - (i * 0.1))
                        
                        predictions.append({
                            'disease': disease,
                            'confidence': confidence,
                            'source': 'model'
                        })
            
            # Remove duplicates and return top predictions
            unique_predictions = {}
            for pred in predictions:
                disease_key = pred['disease'].lower()
                if disease_key not in unique_predictions:
                    unique_predictions[disease_key] = pred
            
            return sorted(unique_predictions.values(), key=lambda x: x['confidence'], reverse=True)[:top_n]
            
        except Exception as e:
            logger.error(f"Error in model prediction: {e}")
            return [{"disease": "Model prediction failed", "confidence": 0.0, "source": "error"}]
    
    def is_emergency(self, symptoms: str) -> bool:
        """Check if symptoms indicate an emergency."""
        symptoms_lower = symptoms.lower()
        return any(emergency in symptoms_lower for emergency in self.emergency_symptoms)
    
    def get_recommendation(self, predictions: List[Dict], symptoms: str) -> str:
        """Generate recommendation based on predictions."""
        if self.is_emergency(symptoms):
            return "🚨 EMERGENCY: Your symptoms may indicate a serious condition. Please seek immediate medical attention or call emergency services!"
        
        if not predictions or predictions[0]['confidence'] < 0.3:
            return "I need more specific symptoms to provide a better assessment. Please describe your symptoms in more detail, or consult a healthcare provider."
        
        best_prediction = predictions[0]
        confidence = best_prediction['confidence']
        disease = best_prediction['disease']
        
        if confidence >= 0.8:
            return f"Based on your symptoms, this could be {disease}. Please consult a healthcare provider for proper diagnosis and treatment."
        elif confidence >= 0.5:
            return f"Your symptoms might suggest {disease}, but I recommend getting a professional medical opinion for accurate diagnosis."
        else:
            return f"Possible condition: {disease}. However, I'm not very confident about this assessment. Please consult a healthcare provider."

class ChatSession:
    """Manages individual chat sessions with conversation history."""
    
    def __init__(self, session_id: str, chatbot: MedicalChatbot):
        self.session_id = session_id
        self.chatbot = chatbot
        self.conversation_history = []
        self.current_symptoms = []
        
    def process_message(self, message: str) -> Dict:
        """Process a user message and return response."""
        try:
            # Add user message to history
            self.conversation_history.append({"role": "user", "content": message})
            
            # Extract and accumulate symptoms
            new_symptoms = [s.strip() for s in message.split(',') if s.strip()]
            self.current_symptoms.extend(new_symptoms)
            
            # Get all symptoms as a single string
            all_symptoms = ', '.join(self.current_symptoms)
            
            # Get predictions
            predictions = self.chatbot.predict_disease(all_symptoms)
            
            # Generate recommendation
            recommendation = self.chatbot.get_recommendation(predictions, all_symptoms)
            
            # Add bot response to history
            self.conversation_history.append({"role": "bot", "content": recommendation})
            
            return {
                "response": recommendation,
                "predictions": predictions,
                "symptoms": all_symptoms,
                "is_emergency": self.chatbot.is_emergency(all_symptoms)
            }
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            error_response = "I'm sorry, I encountered an error processing your message. Please try again or consult a healthcare provider."
            self.conversation_history.append({"role": "bot", "content": error_response})
            
            return {
                "response": error_response,
                "predictions": [],
                "symptoms": "",
                "is_emergency": False,
                "error": str(e)
            }
    
    def get_conversation_history(self) -> List[Dict]:
        """Get the conversation history."""
        return self.conversation_history
    
    def clear_session(self):
        """Clear the session data."""
        self.conversation_history = []
        self.current_symptoms = []

