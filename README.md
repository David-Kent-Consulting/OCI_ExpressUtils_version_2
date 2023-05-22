OCI Express Utilities version 22.May.2023.1
===========================================

[Please consult the license file prior to use of these utililes by clicking on this link](master/dev/LICENSE.txt)

[Please consult the Oracle license agreement for use of Oracle's python SDK APIs for Oracle Cloud Infrastructure by clicking on this link](https://www.oracle.com/us/corporate/contracts/olsa-services/olsa-renewals-en-us-v053012-1867431.pdf)

We recommend installing these tools as a micro service. This micro service can be Docker Desktop, Docker CLI, Azure DevOps, or another DevOps tools. We recommend deploying Ubuntu 20.x or later if installing Docker CLI.
[Please consult the docker file by clicking on this link](master/docker/Dockerfile)

Use Case for These Tools
========================
It is well known that the OCI CLI tools provided by Oracle have limitations. These tools were originally developed by Hank Wojteczko of Kent Cloud Solutions, Inc., as an effort to work past many of the limitations
of the OCI CLI. We note that OCI CLI and OCI Terraform have greatly matured since these utilities were
originally developed. The original utilities for creating, updating, and terminating cloud resources have
been left in the repository. Note however we now use Terraform for the stand-up of new cloud infrastructure.
Note however many of the utilities here are very useful for performing actions like starting/stopping
certain services, and listing information about resources are still used by the cloud team. We also find
the utilities for exporting and importing security lists/security groups to/from CSV format to be very
useful.

Continued Maintenance of This Codebase
======================================
We cannot guarantee that this code base will be maintained in the future. Note however that all of the class
methods used are directly from the Oracle python SDK. The documentation and code examples from Oracle are for the most part very well done. [You can learn more about the Oracle OCI python SDK by clicking here.](https://docs.oracle.com/en-us/iaas/Content/API/SDKDocs/pythonsdk.htm#SDK_for_Python)

