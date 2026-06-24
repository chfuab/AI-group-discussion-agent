feedback_with_err_msg_prompt = """
You are data analyst mastering writing and debugging SQL / NoSQL commands.
Your task here is to generate feedback for the SQL / NoSQL command (the original query code below) based on error messages returned after executing the command.
Please plan and analyze before generation, just hidden and do not generate your plan in the response

You can reference to below items related to original query command during the rewriting process:
    1. Original query expressed in natural language form convertible to SQL / NoSQL command:
    {verifiable_prompt}
    2. Original query_plan for generating the query raising error during its execution:
    {the_original_query_plan} 
    3. Original query command raising error during its execution
    {the_original_query_code} 
    4. Error messages arisen during executing the query command not yet rewritten
    {the_error_message}

Respond in valid JSON format with these keys:
    feedback: [SENTENCE: feedback generated from error messages on the original query]
    retry: [SENTENCE: number of retry of rewriting the query based on feedback generated]
"""

clarification_prompt="""
{role_description}
You are now given a natural language statement below. Please judge whether the statement is satisfied or not based on your domain knowledge. 
    The natural language statement: {natural_language_prompt}

Follow below two steps during the judgement: 
    Step 1: Generate query in natural language able to gather relevant and sufficient information where the judgement is based on
    Step 2: Generate analysis plan on the information expected to be gathered using the query in step 1 above such that the natural language statement above can be judged statisfied or not.

Respond in valid JSON format with these keys:
    verifiable_prompt: [SENTENCE: The natural language query in step 1 above convertable to SQL or NoSQL commands]
    analysis_statement: [SENTENCE: The analysis plan in step 2 above which is able to judge satisfaction of the original natural language statement]
"""

gen_query_prompt = """
You are a data analyst specialized in querying SQL and NoSQL databases.
You are now given a natural language query and are asked to convert it into SQL or NoSQL command, please follow below instruction for the generation:
    1. Plan before generating the command, generate the plan separately in the response
    2. Query the databases based on schema / metadata of the databsaes provided below. Do not skip this step.
    3. Double check the generated command and do correction if necessary
    4. If there is feedback from error messages, you must consider the feedback during generating the commands
    5. DO NOT make any DML statements (INSERT, UPDATE, DELETE, DROP etc.) to the database.
The natural language query: 
    {verify_prompt}
The schema / metadata of SQL database: 
    {SQL_metadata}
The schema / metadata of NoSQL database:
    {NoSQL_metadata}
Feedback from error message:
    {feedback}

After generating the SQL / NoSQL command, execute them to retrieve information from databases    

Respond in valid JSON format with these keys:
    query_code: [SENTENCE: the generated SQL / NoSQL command following instruction 1-5 above]
    query_plan: [SENTENCE: the plan of generating the SQL / NoSQL command as stated in instruction 1 above]
"""

analysis_prompt = """
You are a data analyst specialized in analyzing the data queried from SQL / NoSQL database.
Your task here is to analyze the information gathered from querying databases (namely query result below), by following the analysis plan (called analysis statement below), such that determining whether the original natural language statement is satisfied or not.

Original natural language statement:
{natural_language_prompt}
Query result:
{query_result} 
Analysis statement:
{analysis_statement}

Respond in valid JSON format with these keys:
    verification_decision: [BOOLEAN: whether the original natural language statement above is satisfied or not given query result and analysis statement above]
    verification_result: [SENTENCE: A conclusive statement over the query result and the subsequent analysis about the satisfaction of the original natural language statement]
"""

list_factors_prompt = """
You are a researcher with deep understanding on scientific concepts.
You are given a scientific statement below. 
    The scientific statement: {original_ideas}

You are also given a set of already satisfied conditions expressed in natural language string concatenated in a paragraph as below:
    The already satisfied conditions: {combined_verification_result}

Your task is to list out all conditions (other than those listed above) to be satisfied such that the scientific statement above is satisfied.
Also, please state clearly the relations between each condition, such that for each condition, there would be some conditions depending on it and some conditions determining it. 

Return the listed conditions and relations in a JSON array where each element is an object with:
- "the_condition": the condition listed (string)
- "conditions_that_causing_it": an array of conditions causing the condition stated in "the_condition" above (list of strings)
- "conditions_that_caused_by_it": an array of conditions caused by the condition stated in "the_condition" above (list of strings)

Return ONLY valid JSON. No markdown, no extra text.
Example format:
[
{
"the_condition": "Reproducible synthesis route documented in at least two independent DAC laboratories using same or equivalent pressure calibration and heating protocol",
"conditions_that_causing_it": ["Synthesizability of the material under DAC conditions (150-200 GPa, 2000-2500 K laser heating) with > 90% yield of target phase, verified by synchrotron XRD", "Achieve and maintain a homogeneous sample environment above 1 Mbar (specifically 150-200 GPa) within a Diamond Anvil Cell, using neon or argon as pressure-transmitting medium to minimize deviatoric stress, with in situ laser heating (both sides, 5-10 μm spot) to 2000-2500 K for 1-10 minutes to complete reaction between metal foil and H₂"],
"conditions_that_caused_by_it": ["Synthesizability of the material under DAC conditions (150-200 GPa, 2000-2500 K laser heating) with > 90% yield of target phase, verified by synchrotron XRD"]: 
},
{
"the_condition": "Thermodynamic stability of the high-Tc phase at 200 K and at synthesis pressure (150-200 GPa), and ideally quenchable to ambient pressure (if not, demonstration at high pressure still counts)",
"conditions_that_causing_it": ["Specific crystal structure enabling high Tc (e.g., clathrate hydride LaH₁₀, YH₆, or CaH₆ with Fm3m or P6₃/mmc symmetry), stabilized within DAC at 150-200 GPa and laser heating to 2000-2500 K", "Synthesizability of the material under DAC conditions (150-200 GPa, 2000-2500 K laser heating) with > 90% yield of target phase, verified by synchrotron XRD"],
"conditions_that_caused_by_it": ["Specific crystal structure enabling high Tc (e.g., clathrate hydride LaH₁₀, YH₆, or CaH₆ with Fm3m or P6₃/mmc symmetry), stabilized within DAC at 150-200 GPa and laser heating to 2000-2500 K"]
}
]
"""

explain_prompt = """
You are both a researcher familiar with scientific concepts and a data analyst familiar with interpreting query result from SQL / NoSQL databases.
You are given a natural language statement and verification result (A conclusive statement over the query result and the subsequent analysis about the satisfaction of the original natural language statement) below. Your task is to explain why the result is negating the statement.

The verification result:
    {verification_result}
The natural language statement:
    {original_ideas}

Follow below instruction when providing your explanation:
    - Give your explanation based on knowledge you already have or information searched from internet if necessary. 
    - Provide evidence or number to support your explanation if nnecessary.
    
Respond in valid JSON format with these keys:
    explanation: [SENTENCE: The explanation of why the verification result above is negating the natural language statement above]
"""