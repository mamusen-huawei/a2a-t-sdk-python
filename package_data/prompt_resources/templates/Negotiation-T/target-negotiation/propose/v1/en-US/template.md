## Target Negotiation
{{target_negotiation_summary}} (required)
Requirement:
Please generate the target negotiation summary according to the following requirements:
1. State the source section of the "understanding content" in this round's message, and distinguish by round:
   - If it is the first round of negotiation (this round's message contains <Intent Understanding Statement>), reference <Intent Understanding Statement>
   - If it is a non-first round of negotiation (this round's message is a response to the previous round's questions, containing <Understanding Alignment and Clarification>), reference <Understanding Alignment and Clarification>
2. If there are points to be clarified in this round, reference <Content to Clarify> and indicate that clarification is needed
3. Explicitly state the action expected of the counterparty in this round, such as "please clarify and confirm". The action statement must correspond to the actual section content of this round (e.g., when this round only needs to confirm understanding with no new questions, the action should be "please confirm")
4. Summarize the core theme of the points to be clarified in this round. The summary must remain concise, limited to one or two sentences, and must not expand or restate the specific content in <Intent Understanding Statement> or <Content to Clarify>

Example 1: For the intent understanding of the wireless energy saving optimization task, see <Intent Understanding Statement>. There are questions about the area and the energy saving time range. See <Content to Clarify> for details. Please clarify and confirm.
Example 2: Clarification has been provided for the energy saving time range in the wireless energy saving optimization task. See <Understanding Alignment and Clarification> for details. There are still questions about the area information. See <Content to Clarify> for details. Please clarify and confirm.
Example 3: Clarification has been provided for the area information in the wireless energy saving optimization task. See <Understanding Alignment and Clarification> for details. Please confirm.

## Intent Understanding Statement
{{intent_understanding_statement}} (optional)
Requirement:
Please provide the understanding of the original intent according to the following requirements:
1. It must be a restatement of the original request, and must not introduce new assumptions that do not exist in the original request
2. Each understanding must be annotated with its source, indicating from which field/statement of the original request it is inferred
3. The coverage must be complete: list the understanding of the complete content of the original intent, not only the uncertain parts

## Understanding Alignment and Clarification
{{understanding_alignment_and_clarification}} (optional)
Requirement:
1. The coverage must be complete: for each understanding listed in <Intent Understanding Statement> and each question listed in <Content to Clarify>, a response must be given one by one, without omission, and without skipping and then uniformly stating "the rest are agreed"
2. Response to understanding statements:
   - The confirmation result must be clearly marked as confirmed (agreed) or corrected (needs correction)
   - If corrected, the corrected correct value must be given, and the reason for the correction must be stated. It is not allowed to only mark "incorrect" without giving the correct content
3. The response to question points must correspond to the candidate form given when the question was asked:
   - If the questioner gave closed candidates, the response must directly select the candidate number, and must not deviate from the candidates to give a free description
   - If the candidates include a "none of the above/other" option and it is selected, specific explanation must be supplemented. It is not allowed to only select that option without giving content
   - If the questioner marked it as an open-ended question, the response should be given in a structured "field path + value" form, avoiding a whole paragraph of free text
   - If it is truly impossible to answer, mark it as unable-to-answer and state the reason (such as insufficient permissions, information temporarily unavailable). It is not allowed to leave it blank or replace a clear "cannot answer" with vague language
4. The response scope must strictly align with the field scope of the statements/questions:
   - Must not introduce new field confirmations or new questions outside the statements and questions in this section
5. The response content must maintain the same atomic granularity as the original question points: one question point corresponds to only one response. The responses to multiple question points must not be merged into one comprehensive statement

## Content to Clarify
{{content_to_clarify}} (optional)
Requirement:
For each item to be clarified, the following requirements must be met:
1. It must be locatable to a specific field, and cannot be a general "target unclear"
2. If there are candidate options, please provide them, to avoid free-form description
3. State why the question is raised (optional)
