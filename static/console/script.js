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

    btnSaveChanges.addEventListener('click', () => {
        const userId = editUserIdInput.value.trim();
        const nombre = editNombreInput.value.trim();
        const fechaNacimiento = editFechaNacimientoInput.value.trim();
        const fechaIngreso = editFechaIngresoInput.value.trim();
        const fechaCorte = editFechaCorteInput.value.trim();
        const montoPagan = editMontoPaganInput.value.trim();

        // Enviar los datos actualizados al servidor
        sendUpdatedProspectData(userId, nombre, fechaNacimiento, fechaIngreso, fechaCorte, montoPagan);
    });

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
        } catch (error) {
            console.error('Error al cargar los datos del prospecto:', error);
            const editResponseMessageDiv = document.getElementById('editResponseMessage');
            editResponseMessageDiv.textContent = `Error al cargar los datos del prospecto: ${error.message}`;
            editResponseMessageDiv.classList.add('error');
        }
    }
});

fetchProspects();
async function sendUpdatedProspectData(userId, nombre, fechaNacimiento, fechaIngreso, fechaCorte, montoPagan) {
    const editResponseMessageDiv = document.getElementById('editResponseMessage');
    editResponseMessageDiv.textContent = 'Procesando...';
    editResponseMessageDiv.className = 'message-area';

    if (!userId) {
        editResponseMessageDiv.textContent = 'Error: El User ID no puede estar vacío.';
        editResponseMessageDiv.classList.add('error');
        return;
    }

    try {
        const response = await fetch('/update_prospect', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                user_id: userId,
                nombre: nombre,
                fecha_nacimiento: fechaNacimiento,
                fecha_ingreso: fechaIngreso,
                fecha_corte: fechaCorte,
                monto_pagan: montoPagan
            })
        });
        
        const data = await response.json();

        if (response.ok) {
            editResponseMessageDiv.textContent = `Éxito: ${data.status || JSON.stringify(data)}`;
            editResponseMessageDiv.classList.add('success');
        } else {
            editResponseMessageDiv.textContent = `Error: ${data.error || response.statusText || 'Error desconocido'}`;
            editResponseMessageDiv.classList.add('error');
        }
    } catch (error) {
        console.error('Error en la solicitud:', error);
        editResponseMessageDiv.textContent = `Error de red o conexión: ${error.message}`;
        editResponseMessageDiv.classList.add('error');
    }
}
// Modificar función fetchWaitingUsers
async function fetchWaitingUsers() {
    const response = await fetch('/waiting_users');
    const data = await response.json();
    console.log('--- WAITING USERS:', data.waiting_users);
    renderWaitingUsers(data.waiting_users);
}

// Agregar intervalo de actualización automática
setInterval(fetchWaitingUsers, 15000); // Actualizar cada 15 segundos

function highlightWaitingUser(userId) {
    const waitingUsersList = document.getElementById('waitingUsersList');
    if (!waitingUsersList) {
        console.error('No se encontró la lista de usuarios esperando atención');
        return;
    }

    const userElements = waitingUsersList.querySelectorAll('.user-id-item');
    userElements.forEach(element => {
        if (element.textContent.includes(userId)) {
            element.classList.add('highlighted');
        } else {
            element.classList.remove('highlighted');
        }
    });
}
