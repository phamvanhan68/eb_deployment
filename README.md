#EB Deployment

I will note here all the steps to deploy application to AWS EB

Notes:
1 - We can only connect to EC@ that created by EBS via EC2 Instance Connect
    To do that, there is a prerequisite: SSH - PORT 22 -> needs to OPEN
    We can edit it by go to: SECUTRITY GROUP ->  Edit inbound rules
    IMPORTANT:
        User name to need to fill up: ec2-user

2 - Cronjob
  Docs: https://aws.amazon.com/premiumsupport/knowledge-center/cron-job-elastic-beanstalk/
  See files: cron-linux.config && update_sha.sh && update_sha.py for more information

3 - Application will be located at /var/app/current
  There is no application name 

  