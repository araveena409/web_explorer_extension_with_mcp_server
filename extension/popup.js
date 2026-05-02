document.addEventListener('DOMContentLoaded', () => {
    const submitBtn = document.getElementById('submitBtn');
    const promptInput = document.getElementById('promptInput');
    const results = document.getElementById('results');
    const loader = document.getElementById('loader');
    
    const textContent = document.getElementById('textContent');
    const prefabContainer = document.getElementById('prefabContainer');
    const fileContent = document.getElementById('fileContent');

    submitBtn.addEventListener('click', async () => {
        const prompt = promptInput.value.trim();
        if (!prompt) return;

        // Reset UI
        results.classList.add('hidden');
        loader.classList.remove('hidden');
        prefabContainer.innerHTML = '';
        
        try {
            const response = await fetch('http://127.0.0.1:8000/process', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ prompt })
            });

            if (!response.ok) throw new Error('Agent communication failed');

            const data = await response.json();
            
            // Render Text
            textContent.innerText = data.text || 'No text response returned.';

            // Render PreFab UI
            if (data.ui) {
                renderPrefab(data.ui);
            } else {
                prefabContainer.innerText = 'No UI component data available.';
            }

            // Render File Content
            fileContent.innerText = data.file_content || 'File is empty or could not be read.';

            // Show results
            results.classList.remove('hidden');
        } catch (error) {
            console.error(error);
            alert('Error: ' + error.message);
        } finally {
            loader.classList.add('hidden');
        }
    });

    function renderPrefab(ui) {
        const title = document.createElement('div');
        title.className = 'prefab-title';
        title.innerText = ui.title || 'Data Overview';
        prefabContainer.appendChild(title);

        if (ui.items && Array.isArray(ui.items)) {
            ui.items.forEach(item => {
                const row = document.createElement('div');
                row.className = 'prefab-item';
                
                const label = document.createElement('span');
                label.className = 'prefab-label';
                label.innerText = item.label;
                
                const value = document.createElement('span');
                value.className = 'prefab-value';
                value.innerText = item.value;
                
                row.appendChild(label);
                row.appendChild(value);
                prefabContainer.appendChild(row);
            });
        }
    }
});
