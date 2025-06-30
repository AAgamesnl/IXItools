import openai
import pandas as pd

def get_output():
    # Load the Excel file into a pandas dataframe
    df = pd.read_excel('Data.xlsx')

    # Print the first 40 rows of the dataframe
    text = (pd.read_excel('Data.xlsx').head(40))
    openai.api_key = ''
    # Construct a prompt that asks the model to extract the desired information
    prompt = f"""Geef mij alle details van de klant uit deze tekst geef mij het volledige adres, voor en achternaam. Voor het adres je gebruik je altijd de 2e dat je vindt en gebruik deze formaat:
    NAAM KLANT:
    ADRES PLAATSING KLANT:
    TELEFOON NUMMER KLANT:
    VERDIEPING:
    VOORZIENE PLAATSING WEEK:
    projectnummer:

    {text}

    """

    # Send a completion request to the OpenAI API
    response = openai.Completion.create(
        engine="davinci-002",
        prompt=prompt,
        max_tokens=100,
        temperature=0.3,
    )

    output = response.choices[0].text.strip()

    # Extract data after colon
    data = []
    for line in output.split("\n"):
        colon_index = line.find(":")
        if colon_index != -1:
            data.append(line[colon_index + 1:].strip())

    # Return a list of the extracted data
    return data