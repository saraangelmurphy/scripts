A quick script I made to easily get existing GCP Organization Data into terraform, and into terraform state. 

Get a json formatted list of IAM bindings via `gcloud [organizations | folders | projects] get-iam-policy [org_id | folder_id | project_id ] --format=json > resource_iam.json` and store in the same directory as `tf_generate.py` before executing. 

Produces a generated .tf file you can use to manage the existing organization resources, and a shell script used to import the new resources into your terraform state.

The code is ugly af. TODOs here include: handling IAM conditions and using a real templating engine to generate my tf instead of strings. Or use Go's native HCL interface. Many options better than this!
