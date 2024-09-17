OCI Express Utilities version 2.4.0
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

Utilities Reference
====================
[Click here to access the reference documentation for these tools.](master/DKC%20OCI%20Codebase%20V2.0b.html)
Note it is best if you download the HTML file and reference it locally. You can also download the Word version [by clicking here.](master/dev/DKC%20OCI%20Codebase%20V2.0b.docx)
Click on the link, then click on "View raw," and the file will download.

Required SDK Versions

On OLE 8 and OLE 9, inclusive of container microservices in Docker:
===================================================================
OLE9 recommended, OLE 8.x supported but not recommended
Powershell 7.4.0
Python 3.9.18 on OLE9, Python 3.6.8 on OLE8
Pandas 2.2.2
Tabulate 0.9.0 (Tabulate2 IS NOT supported)
detect_delimiter 0.1.1
OCI python SDK 2.133
Ansible 8.7.0
OCI CLI 3.47.0

On Ubuntu Latest when running in an Azure DevOps microservice pipeline
======================================================================
Python 3.11.10 (OCI CLI not compatible with later versions)
Pandas 2.2.2
Tabulate 0.9.0 (Tabulate2 IS NOT supported)
detect_delimiter 0.1.1
OCI python SDK 2.133
Ansible 8.7.0
OCI CLI 3.47.0

Last Updated
============
17-SEP-2024