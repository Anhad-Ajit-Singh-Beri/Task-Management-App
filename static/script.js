$(document).ready(function () {
    var calendarEl = document.getElementById('calendar');
    var progBar = document.getElementById('progress');

    var calendar = new FullCalendar.Calendar(calendarEl, {
        initialView: 'dayGridMonth', // Set initial view to month view
        events: '/calendar_events', // Endpoint to fetch events from Flask backend
        eventDidMount: function (info) {
            // Optional: Modify event rendering
            info.el.style.backgroundColor = 'red';
        }
    });

    function fetchProgress() {
        $.ajax({
            url: '/progress',
            type: 'GET',
            dataType: 'json',
            success: function (data) {
                console.log(data[0]);
                console.log(data[1]);
                progress = ((data[1] - data[0]) / data[1]) * 100
                console.log(progress)
                progBar.style.width = progress + "%"
            },
            error: function (error) {
                console.error('Error fetching progress:', error);
            }
        });
    }

    fetchProgress()

    function fetchNotif() {
        $.ajax({
            url: '/notification',
            type: 'GET',
            dataType: 'json',
            success: function (data) {
                for (let i = 1; i < data.length; i++) {
                    date = data[i][0].replace('-', ' ').replace('-', ' ');
                    if (data[0] == date) {

                        (async () => {
                            // create and show the notification
                            const showNotification = () => {
                                // create a new notification
                                const notification = new Notification('Reminder', {
                                    body: 'You have a task due today',
                                    icon: '../static/assests/logo.png'
                                });

                                // close the notification after 10 seconds
                                setTimeout(() => {
                                    notification.close();
                                }, 10 * 1000);

                                // navigate to a URL when clicked
                                notification.addEventListener('click', () => {
                                    // Add action here to highlight the task or go to project where task is
                                });
                            }

                            // show an error message
                            const showError = () => {
                                const error = document.querySelector('.error');
                                error.style.display = 'block';
                                error.textContent = 'You blocked the notifications';
                            }

                            // check notification permission
                            let granted = false;

                            if (Notification.permission === 'granted') {
                                granted = true;
                            } else if (Notification.permission !== 'denied') {
                                let permission = await Notification.requestPermission();
                                granted = permission === 'granted' ? true : false;
                            }

                            // show notification or error
                            granted ? showNotification() : showError();

                        })();

                    }
                }

            },
            error: function (error) {
                console.error('Error fetching notifications:', error);
            }
        });
    }

    fetchNotif()
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

document.addEventListener("DOMContentLoaded", function() {
    const trackerContainer = document.querySelector('.tracker');
    const trackButton = document.getElementById('track-button');
    const totalBoxes = 400;  // You can change this number to set the number of boxes
    let currentCount = 0;

    // Create boxes
    for (let i = 0; i < totalBoxes; i++) {
        const box = document.createElement('div');
        box.classList.add('box');
        trackerContainer.appendChild(box);
    }

    // Handle button click
    trackButton.addEventListener('click', function() {
        if (currentCount < totalBoxes) {
            const boxes = document.querySelectorAll('.box');
            boxes[currentCount].classList.add('lit');
            currentCount++;
        }
    });
});
