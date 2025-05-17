document.addEventListener('DOMContentLoaded', () => {
    const userIdInput = document.getElementById('user_id');
    const btnHumanIntervention = document.getElementById('btnHumanIntervention');
    const btnBotIntervention = document.getElementById('btnBotIntervention');
    const btnResetChat = document.getElementById('btnResetChat');
    const responseMessageDiv = document.getElementById('responseMessage');
    const waitingUsersListDiv = document.getElementById('waitingUsersList');
    const btnRefreshWaitingList = document.getElementById('btnRefreshWaitingList');
    const prospectsListDiv = document.getElementById('prospectsList');
    const btnRefreshProspectsList = document.getElementById('btnRefreshProspectsList');
    const prospectSearchInput = document.getElementById('prospectSearchInput'); // Nuevo campo de búsqueda
    const tabButtons = document.querySelectorAll('nav button');
    const tabContents = document.querySelectorAll('.tab-content');
    const editUserIdInput = document.getElementById('edit_user_id');
    const editNombreInput = document.getElementById('edit_nombre');
    const editFechaNacimientoInput = document.getElementById('edit_fecha_nacimiento');
    const editFechaIngresoInput = document.getElementById('edit_fecha_ingreso');
    const editFechaCorteInput = document.getElementById('edit_fecha_corte');
    const editMontoPaganInput = document.getElementById('edit_monto_pagan');
    const btnSaveChanges = document.getElementById('btnSaveChanges');
    const takeControlUserIdInput = document.getElementById('take_control_user_id');
    const takeControlResponseMessageDiv = document.getElementById('take_control_responseMessage');

    const API_BASE_URL = ''; // Se deja vacío para usar la misma URL base del servidor que sirve la consola

    // Función para mostrar una pestaña y ocultar las demás
    function showTab(tabId) {
        tabContents.forEach(content => {
            content.style.display = content.id === tabId ? 'block' : 'none';
        });
        tabButtons.forEach(button => {
            button.classList.toggle('active', button.dataset.tab === tabId);
        });
    }

    // Asignar evento de clic a los botones de navegación
    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            showTab(button.dataset.tab);
        });
    });

    // Mostrar la pestaña "Tomar Control" por defecto
    showTab('take_control');

    async function sendRequest(endpoint, userId, messageArea) {
        messageArea.textContent = 'Procesando...';
        messageArea.className = 'message-area'; // Reset class

        if (!userId) {
            messageArea.textContent = 'Error: El User ID no puede estar vacío.';
            messageArea.classList.add('error');
            return;
        }

        try {
            const response = await fetch(`${API_BASE_URL}${endpoint}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ user_id: userId }),
            });

            const data = await response.json();

            if (response.ok) {
                messageArea.textContent = `Éxito: ${data.status || JSON.stringify(data)}`;
                messageArea.classList.add('success');
                // Actualizar la lista de espera si la acción podría haberla afectado
                if (endpoint === '/human_intervention' || endpoint === '/bot_intervention' || endpoint === '/reset_chat') {
                    fetchWaitingUsers();
                }
            } else {
                messageArea.textContent = `Error: ${data.error || response.statusText || 'Error desconocido'}`;
                messageArea.classList.add('error');
            }
        } catch (error) {
            console.error('Error en la solicitud:', error);
            messageArea.textContent = `Error de red o conexión: ${error.message}`;
            messageArea.classList.add('error');
        }
    }

    btnHumanIntervention.addEventListener('click', () => {
        const userId = takeControlUserIdInput.value.trim();
        sendRequest('/human_intervention', userId, takeControlResponseMessageDiv);
    });

    btnBotIntervention.addEventListener('click', () => {
        const userId = takeControlUserIdInput.value.trim();
        sendRequest('/bot_intervention', userId, takeControlResponseMessageDiv);
    });

    btnResetChat.addEventListener('click', () => {
        const userId = takeControlUserIdInput.value.trim();
        sendRequest('/reset_chat', userId, takeControlResponseMessageDiv);
    });

    // Función para cargar los datos del prospecto en la pestaña "Editar Cliente"
    async function loadProspectData(userId) {
        try {
            const response = await fetch(`${API_BASE_URL}/get_prospect_list`);
            if (!response.ok) {
                const editResponseMessageDiv = document.getElementById('editResponseMessage');
                const errorData = await response.json().catch(() => null);
                throw new Error(`Error del servidor: ${response.status} ${response.statusText} - ${errorData ? errorData.error : 'Desconocido'}`);
            }
            const data = await response.json();
            const prospect = data.prospects.find(p => p.user_id === userId);

            if (prospect) {
                editUserIdInput.value = prospect.user_id;
                editNombreInput.value = prospect.nombre || '';
                editFechaNacimientoInput.value = prospect.fecha_nacimiento || '';
                editFechaIngresoInput.value = prospect.fecha_ingreso || '';
                editFechaCorteInput.value = prospect.fecha_corte || '';
                editMontoPaganInput.value = prospect.monto_pagan || '';
            } else {
                const editResponseMessageDiv = document.getElementById('editResponseMessage');
                editResponseMessageDiv.textContent = `Error: No se encontró el prospecto con ID ${userId}`;
                editResponseMessageDiv.classList.add('error');
            }
        } catch (error) {
            console.error('Error al cargar los datos del prospecto:', error);
            const editResponseMessageDiv = document.getElementById('editResponseMessage');
            editResponseMessageDiv.textContent = `Error al cargar los datos del prospecto: ${error.message}`;
            editResponseMessageDiv.classList.add('error');
        }
    }

    // Modificar el evento de clic en la lista de prospectos para cargar los datos en la pestaña "Editar Cliente"
    let allFetchedProspects = [];
    function renderProspects(prospectsToRender, isFiltering = false) {
        if (!isFiltering) { // Si no estamos filtrando, es una nueva carga de datos
            allFetchedProspects = prospectsToRender; // Guardar la lista completa
        }

        if (!prospectsListDiv) return;
        if (prospectsToRender.length === 0) {
            prospectsListDiv.innerHTML = `<p>${isFiltering ? 'No hay prospectos que coincidan con tu búsqueda.' : 'No hay prospectos para mostrar (con nombre registrado).'}</p>`;
            return;
        }
        prospectsListDiv.innerHTML = ''; // Limpiar
        prospectsToRender.forEach(prospect => {
            const prospectDiv = document.createElement('div');
            prospectDiv.textContent = `${prospect.nombre || 'Sin Nombre'} (${prospect.user_id})`;
            prospectDiv.className = 'user-id-item';
            prospectDiv.style.cursor = 'pointer';

            prospectDiv.addEventListener('click', () => {
                const userIdInput = document.getElementById('user_id');
                userIdInput.value = prospect.user_id;
                userIdInput.focus();

                takeControlUserIdInput.value = prospect.user_id;
                takeControlUserIdInput.focus();
                takeControlResponseMessageDiv.textContent = `User ID '${prospect.user_id}' (${prospect.nombre || 'Sin Nombre'}) seleccionado de la lista de prospectos.`;
                takeControlResponseMessageDiv.className = 'message-area info';
                setTimeout(() => {
                    if (takeControlResponseMessageDiv.textContent === `User ID '${prospect.user_id}' (${prospect.nombre || 'Sin Nombre'}) seleccionado de la lista de prospectos.`) {
                        takeControlResponseMessageDiv.textContent = '';
                        takeControlResponseMessageDiv.className = 'message-area';
                    }
                }, 4000);

                // Cargar los datos del prospecto en la pestaña "Editar Cliente"
                showTab('edit');
                loadProspectData(prospect.user_id);
            });
            prospectsListDiv.appendChild(prospectDiv);
        });
    }

    async function fetchWaitingUsers() {
        waitingUsersListDiv.innerHTML = '<p>Actualizando lista...</p>';
        try {
            const response = await fetch(`${API_BASE_URL}/waiting_users`);
            if (!response.ok) {
                const errorData = await response.json().catch(() => null);
                throw new Error(`Error del servidor: ${response.status} ${response.statusText} - ${errorData ? errorData.error : 'Desconocido'}`);
            }
            const data = await response.json();
            renderWaitingUsers(data.waiting_users || []);
        } catch (error) {
            console.error('Error al obtener usuarios en espera:', error);
            waitingUsersListDiv.innerHTML = `<p class="error-message">Error al cargar lista: ${error.message}</p>`;
        }
    }

    function renderWaitingUsers(users) {
        if (users.length === 0) {
            waitingUsersListDiv.innerHTML = '<p>No hay usuarios esperando atención en este momento.</p>';
        return;
        }
        waitingUsersListDiv.innerHTML = ''; // Limpiar
        users.forEach(userId => {
            const userDiv = document.createElement('div');
            userDiv.textContent = userId;
            userDiv.className = 'user-id-item';
            userDiv.addEventListener('click', () => {
                userIdInput.value = userId;
                userIdInput.focus();
            });
            waitingUsersListDiv.appendChild(userDiv);
        });
    }

    btnRefreshWaitingList.addEventListener('click', fetchWaitingUsers);

    // Cargar la lista al iniciar
    fetchWaitingUsers();

    // --- Lógica para la Lista de Prospectos/Clientes ---
    
    async function fetchProspects() {
        if (!prospectsListDiv) return; // Si el div no existe, no hacer nada
        prospectsListDiv.innerHTML = '<p>Actualizando lista de prospectos...</p>';
        try {
            const response = await fetch(`${API_BASE_URL}/get_prospect_list`);
            if (!response.ok) {
                const errorData = await response.json().catch(() => null);
                throw new Error(`Error del servidor: ${response.status} ${response.statusText} - ${errorData ? errorData.error : 'Desconocido'}`);
            }
            const data = await response.json();
            allFetchedProspects = data.prospects || [];
            renderProspects(allFetchedProspects, false); // Pasar false para isFiltering
        } catch (error) {
            console.error('Error al obtener lista de prospectos:', error);
            prospectsListDiv.innerHTML = `<p class="error-message">Error al cargar lista de prospectos: ${error.message}</p>`;
            allFetchedProspects = []; // Limpiar en caso de error
            renderProspects([], false); // Renderizar lista vacía
        }
    }

    if (prospectSearchInput) {
        prospectSearchInput.addEventListener('input', () => {
            const searchTerm = prospectSearchInput.value.toLowerCase().trim();
            if (!searchTerm) {
                renderProspects(allFetchedProspects, false); // Si no hay término, mostrar todos
            return;
            }
            const filteredProspects = allFetchedProspects.filter(prospect => {
                const nameMatch = prospect.nombre && prospect.nombre.toLowerCase().includes(searchTerm);
                const idMatch = prospect.user_id && prospect.user_id.toLowerCase().includes(searchTerm);
                return nameMatch || idMatch;
            });
            renderProspects(filteredProspects, true); // Pasar true para isFiltering
        });
    }

    btnSaveChanges.addEventListener('click', async () => {
        const userId = editUserIdInput.value.trim();
        const nombre = editNombreInput.value.trim();
        const fechaNacimiento = editFechaNacimientoInput.value.trim();
        const fechaIngreso = editFechaIngresoInput.value.trim();
        const fechaCorte = editFechaCorteInput.value.trim();
        const montoPagan = editMontoPaganInput.value.trim();
        const editResponseMessageDiv = document.getElementById('editResponseMessage');

        if (!userId) {
            editResponseMessageDiv.textContent = 'Error: El User ID no puede estar vacío.';
            editResponseMessageDiv.classList.add('error');
            return;
        }

        btnSaveChanges.style.backgroundColor = '#3498db'; // Cambiar a azul mientras se procesa
        try {
            const response = await fetch(`${API_BASE_URL}/update_prospect`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    user_id: userId,
                    nombre: nombre,
                    fecha_nacimiento: fechaNacimiento,
                    fecha_ingreso: fechaIngreso,
                    fecha_corte: fechaCorte,
                    monto_pagan: montoPagan
                }, null, 2),
            });

            const data = await response.json();

            if (response.ok) {
                editResponseMessageDiv.textContent = `Éxito: Información del usuario ${userId} actualizada correctamente.`;
                editResponseMessageDiv.classList.remove('error');
                editResponseMessageDiv.classList.add('success');
                btnSaveChanges.style.backgroundColor = '#2ecc71'; // Cambiar a verde
                fetchProspects(); // Recargar la lista de prospectos
            } else {
                editResponseMessageDiv.textContent = `Error: ${data.error || response.statusText || 'Error desconocido'}`;
                editResponseMessageDiv.classList.remove('success');
                editResponseMessageDiv.classList.add('error');
                btnSaveChanges.style.backgroundColor = '#e74c3c'; // Mantener rojo o cambiar a otro color de error
            }
        } catch (error) {
            console.error('Error al actualizar la información del prospecto:', error);
            editResponseMessageDiv.textContent = `Error de red o conexión: ${error.message}`;
            editResponseMessageDiv.classList.remove('success');
            editResponseMessageDiv.classList.add('error');
            btnSaveChanges.style.backgroundColor = '#e74c3c'; // Mantener rojo o cambiar a otro color de error
        }
   });

   fetchProspects();
});