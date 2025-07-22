"""
Model loader module for the medical chatbot.
Handles loading and managing the trained model and tokenizer.
"""

import os
import torch
import pandas as pd
from datasets import load_dataset
from transformers import GPT2Tokenizer, GPT2LMHeadModel
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ModelLoader:
    def __init__(self, model_path=None):
        self.model_path = model_path or './symptom_disease_model'
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model = None
        self.tokenizer = None
        self.df = None
        
    def load_model(self):
        """Load the trained model and tokenizer."""
        try:
            if os.path.exists(self.model_path):
                logger.info(f"Loading model from {self.model_path}")
                self.tokenizer = GPT2Tokenizer.from_pretrained(self.model_path)
                self.model = GPT2LMHeadModel.from_pretrained(self.model_path).to(self.device)
                
                # Set padding token
                self.tokenizer.pad_token = self.tokenizer.eos_token
                
                logger.info("Model loaded successfully")
            else:
                logger.warning(f"Model path {self.model_path} not found. Loading base model.")
                self.load_base_model()
                
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            self.load_base_model()
    
    def load_base_model(self):
        """Load the base DistilGPT-2 model if trained model is not available."""
        logger.info("Loading base DistilGPT-2 model")
        self.tokenizer = GPT2Tokenizer.from_pretrained('distilgpt2')
        self.model = GPT2LMHeadModel.from_pretrained('distilgpt2').to(self.device)
        self.tokenizer.pad_token = self.tokenizer.eos_token
        
    def load_dataset(self):
        """Load the medical dataset."""
        try:
            logger.info("Loading medical dataset")
            data_sample = load_dataset("ashnaz/symptoms_diagnose_doctors_data")
            self.df = pd.DataFrame(data_sample['train'])
            
            # Process symptoms column
            self.df['symptoms'] = self.df['symptoms'].apply(
                lambda x: ', '.join(x.split(',')) if isinstance(x, str) else ', '.join(x)
            )
            
            logger.info(f"Dataset loaded with {len(self.df)} records")
            
        except Exception as e:
            logger.error(f"Error loading dataset: {e}")
            # Create a minimal fallback dataset
            self.df = pd.DataFrame({
                'disease': ['flu', 'cold', 'headache'],
                'symptoms': ['fever, cough', 'runny nose, sneezing', 'head pain, nausea']
            })
    
    def get_model_info(self):
        """Get information about the loaded model."""
        return {
            'model_loaded': self.model is not None,
            'tokenizer_loaded': self.tokenizer is not None,
            'dataset_loaded': self.df is not None,
            'device': str(self.device),
            'dataset_size': len(self.df) if self.df is not None else 0
        }

# Global model loader instance
model_loader = ModelLoader()

