from main import App
from core.logger import Logger

app = App()
running = True
started = False

# Start app
try:
    Logger.system("Starting...")
    started = app.start()
except RuntimeError as e:
    Logger.error(e)

# Update app
if started:
    Logger.system("Started")

    while running:
        try:
            running = app.update()
        except RuntimeError as e:
            Logger.error(e)
            running = False

Logger.system("Stopping...")
app.stop()
Logger.system("Stopped")
