## Target Negotiation Result
{{target_negotiation_result}} (required)
Requirement:
1. If all questions can be clarified, return Accept
2. If all questions cannot be fully clarified, return Reject
3. The conclusion must be one of the two, and vague states such as "partially agreed" are not allowed

## Target Negotiation Result Content
{{target_negotiation_result_content}} (required)
Requirement:
1. If all questions can be clarified, list the finally confirmed intent content:
	- Summarize the understandings that have been confirmed or adopted after correction in all rounds of this negotiation, to form a complete and unambiguous final intent description, rather than listing the change process of each round
	- Each item must be directly usable as the basis for subsequent task execution, and must no longer contain uncertain statements such as "to be confirmed" or "may be"
2. If all questions cannot be fully clarified, state the reason for failure
