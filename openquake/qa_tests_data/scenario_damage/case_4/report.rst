Scenario Damage QA Test 4
=========================

============== ===================
checksum32     1,284,787,561      
date           2018-06-26T14:56:59
engine_version 3.2.0-gitb0cd949   
============== ===================

num_sites = 3, num_levels = 60

Parameters
----------
=============================== ==================
calculation_mode                'scenario_damage' 
number_of_logic_tree_samples    0                 
maximum_distance                {'default': 300.0}
investigation_time              None              
ses_per_logic_tree_path         1                 
truncation_level                3.0               
rupture_mesh_spacing            10.0              
complex_fault_mesh_spacing      10.0              
width_of_mfd_bin                None              
area_source_discretization      None              
ground_motion_correlation_model None              
minimum_intensity               {}                
random_seed                     3                 
master_seed                     0                 
ses_seed                        42                
=============================== ==================

Input files
-----------
==================== ============================================
Name                 File                                        
==================== ============================================
exposure             `exposure_model.xml <exposure_model.xml>`_  
job_ini              `job_haz.ini <job_haz.ini>`_                
rupture_model        `fault_rupture.xml <fault_rupture.xml>`_    
structural_fragility `fragility_model.xml <fragility_model.xml>`_
==================== ============================================

Composite source model
----------------------
========= ======= =============== ================
smlt_path weight  gsim_logic_tree num_realizations
========= ======= =============== ================
b_1       1.00000 trivial(1)      1/1             
========= ======= =============== ================

Realizations per (TRT, GSIM)
----------------------------

::

  <RlzsAssoc(size=1, rlzs=1)
  0,ChiouYoungs2008(): [0]>

Exposure model
--------------
=============== ========
#assets         3       
#taxonomies     3       
deductibile     absolute
insurance_limit absolute
=============== ========

======== ======= ====== === === ========= ==========
taxonomy mean    stddev min max num_sites num_assets
RM       1.00000 NaN    1   1   1         1         
RC       1.00000 NaN    1   1   1         1         
W        1.00000 NaN    1   1   1         1         
*ALL*    1.00000 0.0    1   1   3         3         
======== ======= ====== === === ========= ==========

Slowest operations
------------------
======================= ========= ========= ======
operation               time_sec  memory_mb counts
======================= ========= ========= ======
computing gmfs          0.00400   0.0       1     
reading site collection 0.00139   0.0       1     
reading exposure        8.466E-04 0.0       1     
======================= ========= ========= ======