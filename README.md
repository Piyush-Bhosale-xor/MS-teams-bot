Follow the steps below to set up and run the bot locally.

1️⃣ Create and activate a virtual environment
python -m venv env


Activate the environment:

Windows

env\Scripts\activate


macOS / Linux

source env/bin/activate

2️⃣ Install dependencies
pip install -r requirements.txt

3️⃣ Run the application
python app.py


The bot will start and listen at:

http://0.0.0.0:3978/api/messages

4️⃣ Connect to Bot Framework Emulator

Open Bot Framework Emulator

Click Open Bot

Enter the bot URL:

http://0.0.0.0:3978/api/messages
