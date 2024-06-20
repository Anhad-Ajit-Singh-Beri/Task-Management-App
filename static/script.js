$(document).ready(function () {
    var calendarEl = document.getElementById('calendar');

    var calendar = new FullCalendar.Calendar(calendarEl, {
        initialView: 'dayGridMonth', // Set initial view to month view
        events: '/calendar_events', // Endpoint to fetch events from Flask backend
        eventDidMount: function (info) {
            // Optional: Modify event rendering
            info.el.style.backgroundColor = 'red';
        }
    });

    // Function to fetch calendar events manually if needed
    function fetchCalendarEvents() {
        $.ajax({
            url: '/calendar_events',
            type: 'GET',
            dataType: 'json',
            success: function (data) {
                console.log(data); // Log events to console for debugging
                calendar.removeAllEvents(); // Remove all existing events
                calendar.addEventSource(data); // Add new events
            },
            error: function (error) {
                console.error('Error fetching calendar events:', error);
            }
        });
    }

    // Render the calendar when the modal is shown
    $('#calendarModal').on('shown.bs.modal', function () {
        calendar.render();
        fetchCalendarEvents();  // Fetch calendar events when modal is shown
    });

    document.getElementById('fetchEventsButton').addEventListener('click', fetchCalendarEvents);
});

let timer;
let isRunning = false;
let isWorkSession = true;
let workTime = 1500;
let breakTime = 300;
let timeLeft = workTime;

function updateDisplay() {
    const minutes = Math.floor(timeLeft / 60);
    const seconds = timeLeft % 60;
    document.getElementById('timer-display').innerText = `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
}

function startTimer() {
    if (isRunning) return;
    isRunning = true;
    timer = setInterval(() => {
        timeLeft--;
        updateDisplay();
        if (timeLeft <= 0) {
            isWorkSession = !isWorkSession;
            timeLeft = isWorkSession ? workTime : breakTime;
            updateDisplay();
            if (isRunning) startTimer();
        }
    }, 1000);
}


function stopTimer() {
    clearInterval(timer);
    isRunning = false;
}

function resetTimer() {
    clearInterval(timer);
    isRunning = false;
    timeLeft = isWorkSession ? workTime : breakTime;
    updateDisplay();
}


updateDisplay();
