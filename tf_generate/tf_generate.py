import json
from collections import defaultdict
import logging
import re
import textwrap

# Create a custom log
log = logging.getLogger(__name__)
# Create handlers
log = logging.getLogger('log')
log.setLevel(logging.INFO)
console = logging.StreamHandler()
log.addHandler(console)

# Acceptable Values: organization | folder | project
gcp_resource = "organization"
# Acceptable Values: org_id | folder_id | project
resource_id  = "org_id"

# Iterate through list of bindings
# for each binding identify: IAM principal, role
# Data structure: dict of lists: {principalA: [roleA, roleB], principalB: [roleA, roleC]}
# We organize in this way so that the identity principal is the unit of organization, not the binding
# This makes for easier management in terraform, as permissions management should be understood group by group


def organize_bindings_by_groups(data):
    '''Accepts json formatted iam bindings. Returns a dictionary in the form
    memberA: [(roleA), (RoleB, ConditionB), (RoleC)], memberB: [(roleA), (roleB)]'''
    # defining dictionary
    iam_dict = defaultdict(list)
    for binding in data["bindings"]:
        print(f"binding: {binding}")
        if 'condition' in binding:
            # Skip to avoid some complexity when generating TF
            continue
        for member in binding['members']:
            log.info(f"role:{binding['role']}")
            print(f"member:{member}")
            iam_dict[member].append(binding['role'])
    return iam_dict


# This function really be broken up into multiple functions
def generate_terraform(formatted_bindings):
    '''Takes a member-formatted list of IAM bindings, generates a file with the
    google_[project/organization]_iam_member resource blocks for terraform'''
    log.info(f"formatted binding: {formatted_bindings}")
    tf_locals_string = '''locals {'''
    tf_resources_string = ''''''
    shell_string = '''#/bin/bash'''
    for member in formatted_bindings:
        # Format
        # select text before "@"
        # replace all special characters with "_"
        formatted_member_name = str.lower(re.sub('[-.:]', '_', re.search('(^)(.*?)(?=@)', member).group(0)))
        formatted_roles = json.dumps(formatted_bindings[member])
        # Add to locals
        tf_local = f"{formatted_member_name}_roles = {formatted_roles}"
        tf_locals_string = tf_locals_string + "\n    " + tf_local
        # Add to resources
        tf_resource = textwrap.dedent(f'''\
resource "google_{gcp_resource}_iam_member" "{formatted_member_name}_bindings" {{
  for_each = toset(local.{formatted_member_name}_roles)
  org_id   = var.org_id
  role     = each.key
  member   = "{member}"
}}
''')
        tf_resources_string = tf_resources_string + "\n" + tf_resource
        log.info(formatted_member_name)
        log.info(member)
        # Generate shell string
        for role in formatted_bindings[member]:
            tf_import = f"terraform import 'google_{gcp_resource}_iam_member.{formatted_member_name}_bindings[\"{role}\"]' \"{resource_id} {role} {member}\" "
            shell_string = shell_string + "\n" + tf_import
    # Add closing bracket to locals
    tf_locals_string = tf_locals_string + '''\n}\n'''
    # Combined terraform fragments
    tf_string = tf_locals_string + tf_resources_string
    log.info("terraform: " + tf_string)
    log.info("shell: " + shell_string)
    return tf_string, shell_string


# gcloud [organizations | folders | projects] get-iam-policy [org_id | folder_id | project_id ] --format=json > resource_iam.json
with open("resource_iam.json", "r") as f:
    data = json.loads(f.read())
# reorganize data from binding of a role to members, to members to roles
formatted_iam = organize_bindings_by_groups(data)
log.info(json.dumps(formatted_iam, indent=4))
# Generate the terraform confirmation and the shell script to import resources
terraform, script = generate_terraform(dict(formatted_iam))
# Create terraform file
with open('generated_tf.tf', 'w') as outfile:
    outfile.write(terraform)
# Create import shellfile
with open('generated_script.sh', 'w') as outfile:
    outfile.write(script)
