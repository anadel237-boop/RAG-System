document.addEventListener('DOMContentLoaded', () => {
    const queryForm = document.getElementById('queryForm');
    const resultsSection = document.getElementById('resultsSection');
    const loadingState = document.getElementById('loadingState');
    const errorState = document.getElementById('errorState');
    const errorMessage = document.getElementById('errorMessage');
    
    // Elements to update
    const answerContent = document.getElementById('answerContent');
    const confidenceScore = document.getElementById('confidenceScore');
    const processingTime = document.getElementById('processingTime');
    const sourcesList = document.getElementById('sourcesList');

    queryForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const query = document.getElementById('query').value;
        const caseId = document.getElementById('case_id').value;

        // Reset UI
        resultsSection.classList.add('hidden');
        errorState.classList.add('hidden');
        loadingState.classList.remove('hidden');

        try {
            const response = await fetch('/api/medical_query', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                body: JSON.stringify({ 
                    query: query,
                    case_id: caseId || null 
                })
            });

            if (!response.ok) {
                throw new Error(`Server responded with ${response.status}`);
            }

            const result = await response.json();

            if (result.success) {
                displayResults(result);
            } else {
                throw new Error(result.error || 'Unknown error occurred');
            }

        } catch (error) {
            console.error('Query failed:', error);
            showError(error.message);
        } finally {
            loadingState.classList.add('hidden');
        }
    });

    function displayResults(data) {
        // Format answer with line breaks
        const formattedAnswer = data.answer
            .replace(/\n/g, '<br>')
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>'); // Bold markdown
            
        answerContent.innerHTML = formattedAnswer;
        
        // Update meta info
        confidenceScore.textContent = (data.confidence * 100).toFixed(1) + '%';
        processingTime.textContent = data.processing_time.toFixed(2);
        
        // Update sources
        sourcesList.innerHTML = '';
        if (data.sources && data.sources.length > 0) {
            data.sources.forEach(source => {
                const tag = document.createElement('span');
                tag.className = 'source-tag';
                tag.textContent = source;
                sourcesList.appendChild(tag);
            });
        } else {
            sourcesList.innerHTML = '<span class="text-muted">No specific sources cited</span>';
        }

        resultsSection.classList.remove('hidden');
        
        // Scroll to results safely
        try {
            resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
        } catch (e) {
            resultsSection.scrollIntoView();
        }
    }

    function showError(message) {
        errorMessage.textContent = message;
        errorState.classList.remove('hidden');
    }
});
