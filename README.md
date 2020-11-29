# PyPadler :tennis:  

[![serverless](http://public.serverless.com/badges/v3.svg)](http://www.serverless.com)  

PyPadler will help you to get notified by sms when a padel slot is available  
at desired facility and time range.

## Deploy

Follow instructions [here](https://github.com/serverless/serverless/blob/master/README.md) to install the Serverless Framework.

I needed to deactivate Docker feature **Use gRPC FUSE for file sharing** in order do deploy. 
More info about the issue [here](https://github.com/UnitedIncome/serverless-python-requirements/issues/556#issuecomment-728226895).  


### Useful commands

Check if NPM is installed by  
`npm --version`

List installed node packages    
`npm list --depth=0`

Check if Node is installed by  
`node -v`

Make sure all Serverless plugins listed in the "plugins" section of the yml-file is installed.  
`serverless plugin install --name <pluginName>`  

Deploy your function by:  
`serverless deploy --region eu-west-3`  

Invoke your function with logging data:  
`serverless invoke --region eu-west-3 -f hello --log`  

Deploy changes to running function instead of re-deploying entire app ([cli docs](https://www.serverless.com/framework/docs/providers/aws/cli-reference/deploy-function/)):  
`serverless deploy function --function hello --stage dev --region eu-west-3` 
