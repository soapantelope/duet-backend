import random
from pythonosc import udp_client
import openai
from dotenv import load_dotenv
import os
import re
import asyncio
import statistics

load_dotenv()

# Initialize OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")

# Read the prompt file
with open('music_generation_prompt.txt', 'r') as file:
    prompt = file.read()

# Create an OSC client
ip = "127.0.0.1"
port = 4560
client = udp_client.SimpleUDPClient(ip, port)

class MusicGenerator:
    def __init__(self):
        self.last_generation = None
        self.last_focus = None
        self.is_generating = False
        self.lock = asyncio.Lock()

    def format_music_for_prompt(self, result):
        """Convert the music result into a readable format for the prompt"""
        formatted_lines = []
        for item in result:
            if item[0] == 'synth':
                formatted_lines.append(f"synth :{item[1]}, note: :{item[2]}, release: {item[3]}, amp: {item[4]}")
            elif item[0] == 'sleep':
                formatted_lines.append(f"sleep {item[3]}")
        return "\n".join(formatted_lines)

    async def generate_music(self, average_focus):
        """Asynchronous function to generate music using OpenAI"""
        async with self.lock:  # Ensure only one generation happens at a time
            try:
                print("Starting music generation for focus level:", average_focus)
                self.is_generating = True
                
                continuation_prompt = ""
                if self.last_generation and self.last_focus is not None:
                    continuation_prompt = f"""
The previous music segment (at focus level {self.last_focus}/100) was:

{self.format_music_for_prompt(self.last_generation)}

Please create a natural musical continuation that transitions smoothly to the new focus level, maintaining thematic elements where appropriate while adjusting to the new intensity.
"""
                
                response = await asyncio.to_thread(
                    openai.chat.completions.create,
                    messages=[
                        {"role": "system", "content": prompt},
                        {
                            "role": "user",
                            "content": f"Generate music that, on a scale of 1 (very very slow and sad) to 100 (extremely fast, happy, and exciting, with lots of notes), has a value of {average_focus}/100. For higher values of focus, use triplets, 16th notes, sextuplets, and 32nd notes, in increasing order. For lower values of focus, use half notes, whole notes, and dotted half notes, in decreasing order. Use a variety of instruments and dynamics to create a piece that is engaging and exciting.{continuation_prompt}",
                        }
                    ],
                    model="gpt-4o",
                )

                result = []
                lines = response.choices[0].message.content.split('\n')

                synth_pattern = re.compile(r"synth :(\w+), note: :(\w+), release: ([\d.]+), amp: ([\d.]+)")
                sleep_pattern = re.compile(r"sleep ([\d.]+)")
                
                for line in lines:
                    line = line.split('#')[0].strip()
                    
                    match = synth_pattern.match(line)
                    if match:
                        instrument, note, release, amp = match.groups()
                        result.append(['synth', instrument, note, float(release), float(amp)])
                        continue
                    
                    match = sleep_pattern.match(line)
                    if match:
                        duration = float(match.group(1))
                        result.append(['sleep', '', '', duration, ''])

                # Store this generation for next time
                self.last_generation = result
                self.last_focus = average_focus

                # Calculate total duration of the sequence
                total_duration = sum(item[3] for item in result if item[0] == 'sleep')
                print(f"Generated sequence with duration: {total_duration} seconds")

                # Flatten the array
                flattened_data = []
                for sub_array in result:
                    flattened_data.append("START")
                    flattened_data.extend(sub_array)

                # Send OSC message
                client.send_message("/synth", flattened_data)
                if result:  # Only send ambient if we have a result
                    client.send_message("/ambient", result[0][2])

                # Wait for the sequence to complete playing
                # await asyncio.sleep(total_duration)
                # print("Finished playing sequence")
                
            except Exception as e:
                print(f"Error generating music: {e}")
            finally:
                self.is_generating = False

class EEGCollector:
    def __init__(self):
        self.previous_10_focus = [50]
        self.current_average = 50
        self.lock = asyncio.Lock()

    async def collect_data(self):
        """Collect and update EEG data continuously"""
        while True:
            async with self.lock:
                current_focus = random.randint(0, 100)
                self.previous_10_focus.append(current_focus)
                if len(self.previous_10_focus) > 10:
                    self.previous_10_focus.pop(0)
                self.current_average = statistics.mean(self.previous_10_focus)
                print("current average recent focus:", self.current_average)
            await asyncio.sleep(0.2)  # Collection interval

    async def get_average(self):
        """Get the current average focus value"""
        async with self.lock:
            return self.current_average

async def run_music_generation(music_generator, eeg_collector):
    """Run continuous music generation based on EEG data"""
    while True:
        if not music_generator.is_generating:
            average_focus = await eeg_collector.get_average()
            await music_generator.generate_music(average_focus)
        else:
            await asyncio.sleep(0.1)  # Small delay to prevent busy waiting

async def main():
    """Main async function to run both tasks concurrently"""
    music_generator = MusicGenerator()
    eeg_collector = EEGCollector()
    
    try:
        # Run both tasks concurrently
        await asyncio.gather(
            eeg_collector.collect_data(),
            run_music_generation(music_generator, eeg_collector)
        )
    except asyncio.CancelledError:
        print("Tasks cancelled")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Program stopped by user")
