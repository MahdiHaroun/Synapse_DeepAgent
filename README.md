TODO 

Background
image_model gen for anaylis plots " user decide " 
aws SQS Agent 
agents counter by genreated dict

API receives request (thread_id="abc123")
  ↓
Agent calls read_pdf_file()
  ↓
Tool returns: Command(update={"files": {"report.pdf": "..."}})
  ↓
LangGraph merges into state using file_reducer
  ↓
State saved in InMemorySaver with thread_id="abc123"
  ↓
Next request (same thread_id)
  ↓
State loaded → files={...} already populated
  ↓
Tool checks cache before reading disk ✅


Resetting state ensures each new upload is processed cleanly, while not resetting risks mixing data from previous files and producing inconsistent results.



aws s3 must be {admin_folder} ==> many thread folders
