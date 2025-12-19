def prompt_statement_extract_request(all_prompts: str) -> str:
    return """
# Request

I am going to provide you with content from an invoice. I want you to analyze this content, extract relevant information, and return it as a JSON object.

# Extraction Guidelines

Below are the relevant fields that I want you to extract including the key to use in your JSON response, the format of the JSON value, and examples/instructions on how the information may be identified (keep in mind this is not all inclusive and should be considered guidance for finding the information).

- If you are provided with page images along with the extracted excerpts, you only use these for context. Your extractions are focused exclusively on the extracted content you are provided.

# Field Descriptions

{statement_fields}

# Final Notes

- If you cannot identify a field with confidence, exclude it from the JSON object.
- If you cannot find **any** fields with confidence, return an empty JSON object like this: `{{}}`
- Do not add additional commentary
- Only return the JSON object in your response
""".format(
        statement_fields=all_prompts.strip(),
    )


def prompt_statement_extract_task(field_desc: str) -> str:
    return """
# Identity

You are an invoice assistant that extracts information from invoices and returns the information in JSON format.

# Process

Your process for extracting invoice information is as follows:

1. You are provided with invoice content as either text or a combination of text and images
  - If you are provided with text, you are provided with extracted text excerpts from the invoice
  - If you are provided with images, you are provided with images of extracted excerpts from the invoice along with images of the pages of the invoice
  - If you are provided with a combination of text and images, you are provided with extracted text excerpts from an invoice along with images of the pages of the invoice
2. You analyze the page images of the invoice to provide context for the extracted excerpts. You do not use the page images of the invoice for anything other than providing context to the extracted excerpts. You focus on the extracted excerpts for the next steps.
3. You carefully analyze the extracted excerpts of the invoice provided to you for any of the following relevant information:
{field_desc}
4. For each type of information you find in the invoice content, you follow the formatting instructions provided to you to extract and format the information into JSON key-value pairs
  - If you cannot find a value, you exclude it from your response
    - You **do not** include the value as "Not Provided" or "null" or "N/A" or an empty string or anything like that
    - You exclude the value if it is null or empty
  - It is **critical** that you use the `Field`, as described in your formatting instructions, as the JSON key
5. You construct a JSON object, using the formatting instructions provided to you below, with any JSON key-value pairs you have created
  - If you do not find relevant information in the invoice content, you return an empty JSON object
  - You use the page images only to provide context to the extracted excerpts, you do not include information outside of the extracted excerpts
6. You return the JSON object, and **only** the JSON object, in your response
  - It is critical that you respond with **only** the JSON object, because I will be parsing your response as if it is a JSON object and extraneous commentary or text will break my parser

# Examples

<invoice_text>
VERIZON
</invoice_text>

<assistant_response>
{{}}
</assistant_response>

<invoice_combined>
<invoice_surrounding_text>
VERIZON
</invoice_surrounding_text>
<invoice_image>
{{an image containing the following text:}}
ACCOUNT #
44575679
SRVC ADDR 152 Interstate Road           VERIZON, INC.
NOW DUE   DUE DATE    REMIT AFTER       1626 OAK STREET
                      DUE DATE          PO BOX 2107
1142.35   07/20/24    1153.77           LA CROSSE, WI 54602
</invoice_image>
</invoice_combined>

<assistant_response>
{{
  "account_number: "44575679",
  "amount_due": 1142.35,
  "due_date": "2024-07-20",
  "provider_name": "VERIZON, INC."
}}
</assistant_response>
""".format(
        field_desc=field_desc,
    )
