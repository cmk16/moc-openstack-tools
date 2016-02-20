__author__ = 'rahuls@ccs.neu.edu'

import os
import json
import string
import random
import ConfigParser
from keystoneclient.v2_0 import client
from novaclient import client as novaclient

CONFIG_FILE = "settings.ini"

config = ConfigParser.ConfigParser()
config.read(CONFIG_FILE)

admin_user = config.get('auth', 'admin_user')
admin_pwd = config.get('auth', 'admin_pwd')
admin_tenant = config.get('auth', 'admin_tenant')
auth_url = config.get('auth', 'auth_url')

nova_version = config.get('nova', 'version')

email_template = config.get('templates', 'email_template')
password_template = config.get('templates', 'password_template')

email_path = config.get('output', 'email_path')
password_path = config.get('output', 'password_path')


def random_password(size):
    chars = string.ascii_letters + string.digits + string.punctuation[:4]
    return ''.join(random.choice(chars) for _ in range(size))


class Openstack:

    def __init__(self, uname, password, tname, auth_url, nova_version):
        self.keystone = client.Client(username=uname,
                                      password=password,
                                      tenant_name=tname,
                                      auth_url=auth_url)
        self.nova = novaclient.Client(nova_version,
                                      uname,
                                      password,
                                      tname,
                                      auth_url)

    def create_project(self, name, description):
        tenants = [tenant.name for tenant in self.keystone.tenants.list()]
        if name not in tenants:
            print "Tenant not present, creating one."
            tenant = self.keystone.tenants.create(tenant_name=name,
                                                  description=description,
                                                  enabled=True)
            return tenant.id
        else:
            print "Tenant already present. Skip creating it again."
            tenants = [(tenant.name, tenant.id) for tenant in self.keystone.tenants.list()]
            for tenant in tenants:
                if name == tenant[0]:
                    return tenant[1]

    def create_user(self, name, username, password, description, email, tenant_id, proj_name):
        users = [user.name for user in self.keystone.users.list()]
        if username not in users:
            print "User not present, creating it."
            user = self.keystone.users.create(name=username,
                                              email=email,
                                              password=password,
                                              tenant_id=tenant_id)

            dump_email(name, username, proj_name, password)

        else:
            print "User already present, doing nothing"

    def modify_quotas(self, tenant_id, **kwargs):
        """
        modify default quota values for the given tenant.
        kwargs can be cores, fixed_ips, floating_ips, injected_file_content_bytes,
        injected_file_path_bytes, injected_files, instances, key_pairs, metadata_items,
        ram, security_group_rules, security_groups, server_group_members, server_groups
        """
        new_quota = self.nova.quotas.update(tenant_id, **kwargs)
        print "New quota values are: ", new_quota


def dump_email(fullname, username, proj_name, password):
    # This part of code is just to generate the email content
    # The template is available in file pointed by email_template
    # and password_template.
    with open(email_template, "r") as f:
        msg = f.read()

    msg = string.replace(msg, "<USER>", fullname)
    msg = string.replace(msg, "<USERNAME>", username)
    msg = string.replace(msg, "<PROJECTNAME>", proj_name)

    file = email_path + username + ".txt"

    dir = os.path.dirname(file)
    try:
        os.stat(dir)
    except:
        os.mkdir(dir)

    with open(file, "w") as f:
        f.write(msg)

    with open(password_template, "r") as f:
        msg = f.read()

    msg = string.replace(msg, "<USER>", fullname)
    msg = string.replace(msg, "<USERNAME>", username)
    msg = string.replace(msg, "<PASSWORD>", password)

    file = password_path + username + "password.txt"

    dir = os.path.dirname(file)
    try:
        os.stat(dir)
    except:
        os.mkdir(dir)

    with open(file, "w") as f:
        f.write(msg)


if __name__ == "__main__":
    openstack = Openstack(admin_user, admin_pwd, admin_tenant, auth_url, nova_version)

    '''
    content = ""
    with open("all_users.txt", "r") as f:
        content = json.loads(f.read())

    for project in content:
        proj_id = openstack.create_project(project, "MOC class project")

        # email id is used as username as well.....
        for user in content[project]:
            password = random_password(16)
            username = user[0]
            email = user[0]
            user_descr = "MOC class user"
            name = user[1]
            openstack.create_user(name, username, password, user_descr, email, proj_id, project)
    '''

    proj_name = raw_input("Enter the new project name: ")
    proj_descr = raw_input("Enter project description: ")
    username = raw_input("Enter the new username for openstack: ")
    fullname = raw_input("Enter full name: ")
    email = raw_input("Enter user's email address: ")
    user_descr = raw_input("Enter user's description: ")

    proj_id = openstack.create_project(proj_name, proj_descr)

    password = random_password(16)
    openstack.create_user(fullname, username, password, user_descr, email, proj_id, proj_name)

    # TODO: modify quotas doesn't work. Need to fix this
    openstack.modify_quotas(proj_id,
                            security_groups=-1,
                            security_group_rules=-1,
                            floating_ips=5)

    print "Done creating accounts."
