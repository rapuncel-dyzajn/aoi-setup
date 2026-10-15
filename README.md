# AOI setup scripts

## Installation and dependencies

Install Ansible according to our documentation at [Getting+Started#Ansible]().

After cloning the repository, you need to install dependencies from [galaxy.ansible.com](https://galaxy.ansible.com)

```sh
ansible-galaxy role install -r requirements.yml
ansible-galaxy collection install -r requirements.yml
```

You must have `sudo` access to servers to run playbooks.
