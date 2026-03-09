#!/bin/bash
# CourtMitra — One-time setup script
# Run this BEFORE the hackathon to pre-install everything

echo "🏛️ Setting up CourtMitra..."

# Install Python dependencies
pip install -r requirements.txt

# Download spaCy model
python -m spacy download en_core_web_sm

# Pre-download sentence-transformers model (saves time on hackathon day)
python -c "
from sentence_transformers import SentenceTransformer
print('Downloading embedding model...')
model = SentenceTransformer('all-MiniLM-L6-v2')
print('✅ Embedding model ready')
"

echo ""
echo "✅ Setup complete!"
echo ""
echo "To run CourtMitra:"
echo "  1. Add your Groq API key to .env: GROQ_API_KEY=your_key_here"
echo "  2. Run: streamlit run app.py"
echo ""
echo "Get a free Groq API key at: https://console.groq.com"
