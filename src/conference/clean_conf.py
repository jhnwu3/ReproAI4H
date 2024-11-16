# Non-Jupyter notebook version
import transformers
import torch
from transformers import BitsAndBytesConfig, pipeline, AutoTokenizer
import pandas as pd
ACCESS_TOKEN = ""
device = "cuda:0"

title_cleaning_prompt = """
You are an assistant specialized in cleaning and standardizing academic paper titles. Your task is to take a given title and improve its formatting, spacing, and consistency. Follow these rules:

1. Correct spacing:
   - Ensure single spaces between words.
   - Remove extra spaces before or after hyphens.
   - Add spaces after colons and semicolons.

2. Hyphenation:
   - Use hyphens consistently in compound terms (e.g., "Multi-Scale" not "Multi Scale" or "MultiScale").
   - Correct common hyphenation errors in technical terms (e.g., "Pre-processing" not "Preprocessing").

3. Capitalization:
   - Use title case: Capitalize the first letter of each major word.
   - Do not capitalize articles (a, an, the), coordinating conjunctions (and, but, for, or, nor), or prepositions unless they start the title.
   - Always capitalize the first and last words of the title and subtitle.

4. Acronyms and initialisms:
   - Remove spaces between letters in acronyms (e.g., "CNN" not "C N N").
   - Ensure correct formatting of technical acronyms (e.g., "U-Net" not "UNet" or "U Net").

5. Special characters:
   - Correct the use of special characters like hyphens (-), en dashes (–), and em dashes (—).
   - Ensure proper use of quotation marks and apostrophes.

6. Consistency:
   - Maintain consistent formatting throughout the title.
   - Ensure that similar terms or concepts are formatted the same way.

7. Grammar and spelling:
   - Correct any obvious spelling errors.
   - Ensure proper grammatical structure.

8. No Authors: If the title contains any author names, emails, or affiliations, remove them.

When given a title, apply these rules to clean and standardize it. Provide the corrected title without additional commentary unless there are ambiguities or decisions that require explanation.

Title to clean: {title}

Cleaned title:
"""

def load_70b_model(device):
    model_id = "aaditya/OpenBioLLM-Llama3-70B"
        # Load model directly

    nf4_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True,
        bnb_4bit_compute_dtype=torch.bfloat16
    )
    model_nf4 = transformers.AutoModelForCausalLM.from_pretrained(model_id, 
                                                    quantization_config=nf4_config,
                                                    device_map={"": device},
                                                    token=ACCESS_TOKEN)
    
    tokenizer = AutoTokenizer.from_pretrained(model_id, token=ACCESS_TOKEN)
    
    pipeline = transformers.pipeline(
        "text-generation",
        model= model_nf4, #model_id,
        # model_kwargs={"torch_dtype": torch.bfloat16},
        tokenizer=tokenizer,
        # device=device,
    )

    messages = [
        {"role": "system", "content": "You are an expert and experienced from the healthcare and biomedical domain with extensive medical knowledge and practical experience. Your name is OpenBioLLM, and your job is to annotate dictionary features and contexts learned by interpretability techniques. Please answer the below message."},
        {"role": "user", "content": "Hello?"},
    ]

    prompt = pipeline.tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True
    )

    terminators = [
        pipeline.tokenizer.eos_token_id,
        pipeline.tokenizer.convert_tokens_to_ids("<|eot_id|>")
    ]

    outputs = pipeline(
        prompt,
        max_new_tokens=256,
        eos_token_id=terminators,
        do_sample=True,
        temperature=0.1,
        top_p=0.9,
    )
    print(outputs[0]["generated_text"][len(prompt):])
    return pipeline

def generate_text_with_icl(prompt, pipeline, task_examples, max_new_tokens=256, temperature=0.00001, top_p=0.99) -> str:
    """
    Generate text using the specified prompt and parameters with in-context learning.
    Args:
    prompt (str): The input prompt for text generation.
    pipeline: The text generation pipeline.
    task_examples (list): List of dictionaries containing input-output pairs for in-context learning.
    max_new_tokens (int, optional): The maximum number of new tokens to generate. Defaults to 256.
    temperature (float, optional): The temperature value for sampling. Defaults to 0.00001.
    top_p (float, optional): The top-p value for sampling. Defaults to 0.99.
    Returns:
    str: The generated text.
    """
    # Construct the in-context learning prompt
    icl_prompt = "You are an expert and experienced from the healthcare and biomedical domain with extensive medical knowledge and practical experience. Your job is to help annotate specific tasks by looking for common patterns within text. Here are some examples of how to perform the task:\n\n"
    
    for example in task_examples:
        icl_prompt += f"Input: {example['input']}\nOutput: {example['output']}\n\n"
    
    icl_prompt += f"Now, please perform the same task for the following input:\nInput: {prompt}\nOutput:"

    messages = [
        {"role": "system", "content": icl_prompt},
        {"role": "user", "content": prompt},
    ]
    
    full_prompt = pipeline.tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True
    )
    
    terminators = [
        pipeline.tokenizer.eos_token_id,
        pipeline.tokenizer.convert_tokens_to_ids("<|eot_id|>")
    ]
    
    outputs = pipeline(
        full_prompt,
        max_new_tokens=max_new_tokens,
        eos_token_id=terminators,
        do_sample=True,
        temperature=temperature,
        top_p=top_p,
    )
    
    return outputs[0]["generated_text"][len(full_prompt):]


def extract_and_clean_emails(text, pipeline):
    prompt = f"""
    Extract all email addresses from the following text.
    Clean the extracted email addresses by removing any unnecessary characters or formatting issues.
    Output only the cleaned email addresses, one per line.
    
    Text: {text}
    
    Cleaned and extracted email addresses:
    """
    # Generate the response
    response = generate_text_with_icl(prompt, pipeline, [{"input": text, "output": ""}], max_new_tokens=256, temperature=0.00001, top_p=0.99)
    return response

def process_dataframe_emails(pipeline, df: pd.DataFrame, text_column: str):
    # Extract and clean emails
    processed_emails = df[text_column].apply(lambda x: extract_and_clean_emails(x, pipeline))
    
    # Create a new dataframe with processed emails
    new_df = df.copy()
    new_df['processed_emails'] = processed_emails
    
    # Reorder columns to put processed_emails right after the original text column
    cols = list(new_df.columns)
    text_index = cols.index(text_column)
    cols.insert(text_index + 1, cols.pop(cols.index('processed_emails')))
    new_df = new_df[cols]
    
    return new_df


def clean_titles(pipeline, df: pd.DataFrame, prompt: str):
    cleaned_titles = []
    for title in df["title"]:
        formatted_prompt = prompt.format(title=title)
        cleaned_title = generate_text_with_icl(formatted_prompt, pipeline, [{"input": formatted_prompt, "output": ""}], max_new_tokens=256, temperature=0.00001, top_p=0.99)
        print(cleaned_title)
        cleaned_titles.append(cleaned_title)
    return cleaned_titles

def process_dataframe_titles(pipeline, df: pd.DataFrame, prompt: str):
    # Clean the titles
    cleaned_titles = clean_titles(pipeline, df, prompt)
    
    # Create a new dataframe with cleaned titles
    new_df = df.copy()
    new_df['cleaned_title'] = cleaned_titles
    
    # Reorder columns to put cleaned_title right after the original title
    cols = list(new_df.columns)
    title_index = cols.index('title')
    cols.insert(title_index + 1, cols.pop(cols.index('cleaned_title')))
    new_df = new_df[cols]
    
    return new_df

def clean_conference_papers(llama3, title_cleaning_prompt, conference="chil"):
    # Load the extracted information
    chil_info = pd.read_csv(f"processed_data/{conference}_extracted_info.csv")
    chil_info = process_dataframe_emails(llama3, chil_info, "authors")
    cleaned_chil_info = process_dataframe_titles(llama3, chil_info, title_cleaning_prompt)
    
    # Display the first 5 rows of the new dataframe
    print(cleaned_chil_info.head())
    # Optionally, save the new dataframe to a CSV file
    cleaned_chil_info.to_csv(f"processed_data/cleaned_{conference}_extracted_info.csv", index=False)


llama3 = load_70b_model(device)

clean_conference_papers(llama3, title_cleaning_prompt, conference="chil")
clean_conference_papers(llama3, title_cleaning_prompt, conference="ml4h")
clean_conference_papers(llama3, title_cleaning_prompt, conference="mlhc")

