import os

settings = {
    'host': os.environ.get('ACCOUNT_HOST', 'https://mywwcosmos.documents.azure.com:443/'),
    'master_key': os.environ.get('ACCOUNT_KEY', 'fpvcC6M5PcgF2uaeAOmqwcZZf8vKo83H1CpzqJSgFb1mKW08Rb7odgekDDPzYakWuvWjifzT7R6kbVMmSHNECw=='),
    'database_id': os.environ.get('COSMOS_DATABASE', 'ToDoList'),
    'container_id': os.environ.get('COSMOS_CONTAINER', 'Items'),
}