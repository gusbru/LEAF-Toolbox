# Classes for SL2P LEAF Toolbox algorithms
# Richard Fernandes December, 2023
# Feacture collections match those use in https://github.com/fqqlsun/LEAF_production/blob/main/LEAFNets.py now   Richard Fernanes Nov 24, 2023

import ee
import toolsNets
import toolsUtils
import dictionariesSL2P
import eoImage

# --------------------
# Generic Functions: 
# --------------------
#simple algorithm class
class algorithm:

    def __init__(self, variableName,collectionName):
        self.cc = self.collectionConstructors()
        self.networkOptions= dictionariesSL2P.make_net_options()[variableName][collectionName]
        self.collectionOptions= dictionariesSL2P.make_collection_options(self.cc)[collectionName]
        self.tools = self.collectionOptions["tools"]

    def __clipPartition(self,image):
        image = ee.Image(image)

        return (self.partition).filterBounds(image.geometry()).mosaic().clip(image.geometry()).rename('partition')
 
    def createInput(self,mapBounds,startDate,endDate,maxCloudcover):
        return  ee.ImageCollection(self.collectionOptions['name']) \
                        .filterBounds(mapBounds) \
                        .filterDate(startDate, endDate) \
                        .filterMetadata(self.collectionOptions["Cloudcover"],'less_than',maxCloudcover) \
                        .limit(5000) \
                        .map(lambda image: image.clip(mapBounds)) \
                        .map(lambda image: self.tools.MaskClear(image))  \
                        .map(lambda image: eoImage.attach_Date(image)) \
                        .map(lambda image: eoImage.attach_LonLat(image)) \
                        .map(lambda image: self.tools.addGeometry(self.collectionOptions,image)) 
                        
    # determine if inputs fall in domain of algorithm
    # need to be updated to allow for the domain to vary with partition
    def invalidInput(Domain,bandList,image):
        Domain = ee.FeatureCollection(Domain).aggregate_array("DomainCode").sort()
        bandList = ee.List(bandList).slice(3)
        image = ee.Image(image)

        # code image bands into a single band and compare to valid codes to make QC band
        image = image.addBands(image.select(bandList).multiply(ee.Image.constant(ee.Number(10))).ceil().mod(ee.Number(10)).uint8()\
                        .multiply(ee.Image.constant(ee.List.sequence(0,bandList.length().subtract(1)).map(lambda value:
                                ee.Number(10).pow(ee.Number(value)))))\
                        .reduce("sum").remap(Domain, ee.List.repeat(0, sl2pDomain.length()),1).rename("QC"))
        return image

    def fit(self):

        self.partition = ee.ImageCollection(self.collectionOptions["partition"])

        #identify the network we need
        numNets = ee.Number(ee.Feature((self.collectionOptions["Network_Ind"]).first()).propertyNames().remove('lon').remove('Feature Index').remove('system:index').size())
        
        # populate the netwoorks for each unique partition class
        net1 = toolsNets.makeNetVars(self.collectionOptions["Collection_SL2P"],numNets,1)
        return ee.List.sequence(1,ee.Number(self.collectionOptions["numVariables"]),1).map(lambda netNum: toolsNets.makeNetVars(self.collectionOptions["Collection_SL2P"],numNets,netNum))
    

    def fitUncertainty(self):

        self.partitionUncertainty = ee.ImageCollection(self.collectionOptions["partition"])

        #identify the network we need
        numNets = ee.Number(ee.Feature((self.collectionOptions["Network_Ind"]).first()).propertyNames().remove('lon').remove('Feature Index').remove('system:index').size())
        
        # populate the netwoorks for each unique partition class
        net1 = toolsNets.makeNetVars(self.collectionOptions["Collection_SL2Perrors"],numNets,1)
        return ee.List.sequence(1,ee.Number(self.collectionOptions["numVariables"]),1).map(lambda netNum: toolsNets.makeNetVars(self.collectionOptions["Collection_SL2Perrors"],numNets,netNum))

    # pre process input imagery and flag invalid inputs
    def preprocessInput(self,input_collection):
        return input_collection.map(lambda image: self.tools.MaskLand(image)).map(lambda image: \
                        toolsUtils.scaleBands(self.networkOptions["inputBands"],self.networkOptions["inputScaling"],self.networkOptions["inputOffset"],image)) \
                                .map(lambda image: toolsUtils.invalidInput(self.collectionOptions["sl2pDomain"],self.networkOptions["inputBands"],image)) 

    def predict(self,name,variable,image):
        image = ee.Image(image)

        return toolsNets.wrapperNNets(self.estimator,self.__clipPartition(image),self.networkOptions,self.collectionOptions,name,variable,image)

    def predictUncertainty(self,name,variable,image):
        image = ee.Image(image)

        return toolsNets.wrapperNNets(self.uncertainty,self.__clipPartition(image),self.networkOptions,self.collectionOptions,name,variable,image)


    class featureCollectionConstructors():

        def __init__(self):
            self.Name = 'SL2PV0'  



        #--------------------------------------------------------------------------------*/
        # Landsat 8 Surface_Reflectance SL2P algoirthm - these are correct RF Nov 2023 */                 
        #--------------------------------------------------------------------------------*/
        def l8_createCollection_Network_Ind(self):
          return ee.FeatureCollection('users/rfernand387/Parameter_file_prosail_ccrs_big_clumped2')

        #old version that used 2015 NA land cover
        # def l8_createImageCollection_partition():
        #     return ee.ImageCollection('users/rfernand387/NA_NALCMS_2015_tiles') \
        #               .map(lambda image :image.select("b1").rename("partition") ) \
        #               .merge(ee.ImageCollection("COPERNICUS/Landcover/100m/Proba-V/Global") \
        #                         .map( lambda image :image.select("discrete_classification").remap([0,20,30,40,50,60,70,80,90,100,111,112,113,114,115,116,121,122,123,124,125,126,200],[0,8,10,15,17,16,19,18,14,13,1,3,1,5,6,6,2,4,2,5,6,6,18],0).toUint8().rename("partition")))

        def l8_createImageCollection_partition(self):
            return ee.ImageCollection(ee.Image('USGS/NLCD_RELEASES/2020_REL/NALCMS')) \
                      .map(lambda image: image.rename("partition") )\
                      .merge(ee.ImageCollection("COPERNICUS/Landcover/100m/Proba-V/Global")\
                                .map( lambda image :image.select("discrete_classification").remap([0,20,30,40,50,60,70,80,90,100,111,112,113,114,115,116,121,122,123,124,125,126,200],[0,8,10,15,17,16,19,18,14,13,1,3,1,5,6,6,2,4,2,5,6,6,18],0).toUint8().rename("partition")))

        def l8_createCollection_legend(self):
            return ee.FeatureCollection('users/rfernand387/Legend_prosail_ccrs_big_clumped')

        def l8_createCollection_estimates(self):
            return  ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l8_sl2p_weiss_or_prosail_NNT1_Single_0_1') \
            .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l8_sl2p_weiss_or_prosail_NNT1_Single_0_1')) \
            .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l8_sl2p_ROF_sobol_prosail_dbf_big_clumpedv3_NNT1_Single_0_1')) \
            .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l8_sl2p_ROF_sobol_prosail_enf_big_clumpedv2_NNT1_Single_0_1')) \
            .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l8_sl2p_weiss_or_prosail_NNT1_Single_0_1')) \
            .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l8_sl2p_weiss_or_prosail_NNT1_Single_0_1')) \
            .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l8_sl2p_weiss_or_prosail_NNT1_Single_0_1')) \
            .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l8_sl2p_ROF_sobol_prosail_dbf_big_clumpedv3_NNT1_Single_0_1')) \
            .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l8_sl2p_weiss_or_prosail_NNT1_Single_0_1')) \
            .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l8_sl2p_weiss_or_prosail_NNT1_Single_0_1')) \
            .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l8_sl2p_weiss_or_prosail_NNT1_Single_0_1')) \
            .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l8_sl2p_ROF_sobol_prosail_mix_big_clumpedv3_NNT1_Single_0_1')) 

        def l8_createCollection_errors(self):
            return  ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l8_sl2p_weiss_or_prosail_NNT1_Single_0_1_incertitudes') \
            .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l8_sl2p_weiss_or_prosail_NNT1_Single_0_1_incertitudes')) \
            .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l8_sl2p_ROF_sobol_prosail_dbf_big_clumpedv3_NNT1_Single_0_1_incertitudes')) \
            .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l8_sl2p_ROF_sobol_prosail_enf_big_clumpedv2_NNT1_Single_0_1_incertitudes')) \
            .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l8_sl2p_weiss_or_prosail_NNT1_Single_0_1_incertitudes')) \
            .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l8_sl2p_weiss_or_prosail_NNT1_Single_0_1_incertitudes')) \
            .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l8_sl2p_weiss_or_prosail_NNT1_Single_0_1_incertitudes')) \
            .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l8_sl2p_ROF_sobol_prosail_dbf_big_clumpedv3_NNT1_Single_0_1_incertitudes')) \
            .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l8_sl2p_weiss_or_prosail_NNT1_Single_0_1_incertitudes')) \
            .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l8_sl2p_weiss_or_prosail_NNT1_Single_0_1_incertitudes')) \
            .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l8_sl2p_weiss_or_prosail_NNT1_Single_0_1_incertitudes')) \
            .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l8_sl2p_ROF_sobol_prosail_mix_big_clumpedv3_NNT1_Single_0_1_incertitudes')) \

        def l8_createCollection_ranges(self):
            return ee.FeatureCollection('users/rfernand387/LANDSAT_LC08_C01_T1_SR/LANDSAT_LC08_C01_T1_SR_SL2P_RANGE')\
                            .merge(ee.FeatureCollection('users/rfernand387/LANDSAT_LC08_C01_T1_SR/LANDSAT_LC08_C01_T1_SR_SL2P_RANGE')) \
                            .merge(ee.FeatureCollection('users/rfernand387/LANDSAT_LC08_C01_T1_SR/LANDSAT_LC08_C01_T1_SR_SL2P_RANGE')) \
                            .merge(ee.FeatureCollection('users/rfernand387/LANDSAT_LC08_C01_T1_SR/LANDSAT_LC08_C01_T1_SR_SL2P_RANGE')) \
                            .merge(ee.FeatureCollection('users/rfernand387/LANDSAT_LC08_C01_T1_SR/LANDSAT_LC08_C01_T1_SR_SL2P_RANGE')) \
                            .merge(ee.FeatureCollection('users/rfernand387/LANDSAT_LC08_C01_T1_SR/LANDSAT_LC08_C01_T1_SR_SL2P_RANGE')) \
                            .merge(ee.FeatureCollection('users/rfernand387/LANDSAT_LC08_C01_T1_SR/LANDSAT_LC08_C01_T1_SR_SL2P_RANGE')) \
                            .merge(ee.FeatureCollection('users/rfernand387/LANDSAT_LC08_C01_T1_SR/LANDSAT_LC08_C01_T1_SR_SL2P_RANGE')) \
                            .merge(ee.FeatureCollection('users/rfernand387/LANDSAT_LC08_C01_T1_SR/LANDSAT_LC08_C01_T1_SR_SL2P_RANGE')) \
                            .merge(ee.FeatureCollection('users/rfernand387/LANDSAT_LC08_C01_T1_SR/LANDSAT_LC08_C01_T1_SR_SL2P_RANGE')) \
                            .merge(ee.FeatureCollection('users/rfernand387/LANDSAT_LC08_C01_T1_SR/LANDSAT_LC08_C01_T1_SR_SL2P_RANGE')) \
                            .merge(ee.FeatureCollection('users/rfernand387/LANDSAT_LC08_C01_T1_SR/LANDSAT_LC08_C01_T1_SR_SL2P_RANGE')) 

        def l8_createCollection_domains(self):
            return  ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l8_sl2p_weiss_or_prosail_domain') \
            .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l8_sl2p_weiss_or_prosail_domain')) \
            .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l8_sl2p_ROF_sobol_prosail_dbf_big_clumpedv3_domain')) \
            .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l8_sl2p_ROF_sobol_prosail_enf_big_clumpedv2_domain')) \
            .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l8_sl2p_weiss_or_prosail_domain')) \
            .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l8_sl2p_weiss_or_prosail_domain')) \
            .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l8_sl2p_weiss_or_prosail_domain')) \
            .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l8_sl2p_ROF_sobol_prosail_dbf_big_clumpedv3_domain')) \
            .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l8_sl2p_weiss_or_prosail_domain')) \
            .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l8_sl2p_weiss_or_prosail_domain')) \
            .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l8_sl2p_weiss_or_prosail_domain')) \
            .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l8_sl2p_ROF_sobol_prosail_mix_big_clumpedv3_domain')) \

        #--------------------------------------------------------------------------------*/
        # Landsat 9 Surface_Reflectance SL2P algoirthm - these are correct RF Nov 2023 */                 
        #--------------------------------------------------------------------------------*/
        def l9_createCollection_Network_Ind(self):
          return ee.FeatureCollection('users/rfernand387/Parameter_file_prosail_ccrs_big_clumped2')


        # old version that used 2015 NA land cover
        # def l8_createImageCollection_partition():
        #     return ee.ImageCollection('users/rfernand387/NA_NALCMS_2015_tiles')\
        #               .map(lambda image :image.select("b1").rename("partition") )\
        #               .merge(ee.ImageCollection("COPERNICUS/Landcover/100m/Proba-V/Global")\
        #                         .map( lambda image :image.select("discrete_classification").remap([0,20,30,40,50,60,70,80,90,100,111,112,113,114,115,116,121,122,123,124,125,126,200],[0,8,10,15,17,16,19,18,14,13,1,3,1,5,6,6,2,4,2,5,6,6,18],0).toUint8().rename("partition")))
        # 

        def l9_createImageCollection_partition(self):
            return ee.ImageCollection(ee.Image('USGS/NLCD_RELEASES/2020_REL/NALCMS'))\
                      .map(lambda image :image.rename("partition"))\
                      .merge(ee.ImageCollection("COPERNICUS/Landcover/100m/Proba-V/Global")\
                                .map( lambda image :image.select("discrete_classification").remap([0,20,30,40,50,60,70,80,90,100,111,112,113,114,115,116,121,122,123,124,125,126,200],[0,8,10,15,17,16,19,18,14,13,1,3,1,5,6,6,2,4,2,5,6,6,18],0).toUint8().rename("partition")))


        def l9_createCollection_legend(self):
            return ee.FeatureCollection('users/rfernand387/Legend_prosail_ccrs_big_clumped')

        def l9_createCollection_estimates(self):
            return  ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l9_sl2p_weiss_or_prosail_NNT1_Single_0_1') \
            .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l9_sl2p_weiss_or_prosail_NNT1_Single_0_1')) \
            .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l8_sl2p_ROF_sobol_prosail_dbf_big_clumpedv3_NNT1_Single_0_1')) \
            .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l8_sl2p_ROF_sobol_prosail_enf_big_clumpedv2_NNT1_Single_0_1')) \
            .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l9_sl2p_weiss_or_prosail_NNT1_Single_0_1')) \
            .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l9_sl2p_weiss_or_prosail_NNT1_Single_0_1')) \
            .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l9_sl2p_weiss_or_prosail_NNT1_Single_0_1')) \
            .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l8_sl2p_ROF_sobol_prosail_dbf_big_clumpedv3_NNT1_Single_0_1')) \
            .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l9_sl2p_weiss_or_prosail_NNT1_Single_0_1')) \
            .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l9_sl2p_weiss_or_prosail_NNT1_Single_0_1')) \
            .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l9_sl2p_weiss_or_prosail_NNT1_Single_0_1')) \
            .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l8_sl2p_ROF_sobol_prosail_mix_big_clumpedv3_NNT1_Single_0_1')) 

        def l9_createCollection_errors(self):
            return  ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l9_sl2p_weiss_or_prosail_NNT1_Single_0_1_incertitudes') \
            .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l9_sl2p_weiss_or_prosail_NNT1_Single_0_1_incertitudes')) \
            .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l8_sl2p_ROF_sobol_prosail_dbf_big_clumpedv3_NNT1_Single_0_1_incertitudes')) \
            .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l8_sl2p_ROF_sobol_prosail_enf_big_clumpedv2_NNT1_Single_0_1_incertitudes')) \
            .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l9_sl2p_weiss_or_prosail_NNT1_Single_0_1_incertitudes')) \
            .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l9_sl2p_weiss_or_prosail_NNT1_Single_0_1_incertitudes')) \
            .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l9_sl2p_weiss_or_prosail_NNT1_Single_0_1_incertitudes')) \
            .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l8_sl2p_ROF_sobol_prosail_dbf_big_clumpedv3_NNT1_Single_0_1_incertitudes')) \
            .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l9_sl2p_weiss_or_prosail_NNT1_Single_0_1_incertitudes')) \
            .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l9_sl2p_weiss_or_prosail_NNT1_Single_0_1_incertitudes')) \
            .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l9_sl2p_weiss_or_prosail_NNT1_Single_0_1_incertitudes')) \
            .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l8_sl2p_ROF_sobol_prosail_mix_big_clumpedv3_NNT1_Single_0_1_incertitudes')) 


        def l9_createCollection_ranges(self):
          return ee.FeatureCollection('users/rfernand387/LANDSAT_LC08_C01_T1_SR/LANDSAT_LC08_C01_T1_SR_SL2P_RANGE')\
                            .merge(ee.FeatureCollection('users/rfernand387/LANDSAT_LC08_C01_T1_SR/LANDSAT_LC08_C01_T1_SR_SL2P_RANGE')) \
                            .merge(ee.FeatureCollection('users/rfernand387/LANDSAT_LC08_C01_T1_SR/LANDSAT_LC08_C01_T1_SR_SL2P_RANGE')) \
                            .merge(ee.FeatureCollection('users/rfernand387/LANDSAT_LC08_C01_T1_SR/LANDSAT_LC08_C01_T1_SR_SL2P_RANGE')) \
                            .merge(ee.FeatureCollection('users/rfernand387/LANDSAT_LC08_C01_T1_SR/LANDSAT_LC08_C01_T1_SR_SL2P_RANGE')) \
                            .merge(ee.FeatureCollection('users/rfernand387/LANDSAT_LC08_C01_T1_SR/LANDSAT_LC08_C01_T1_SR_SL2P_RANGE')) \
                            .merge(ee.FeatureCollection('users/rfernand387/LANDSAT_LC08_C01_T1_SR/LANDSAT_LC08_C01_T1_SR_SL2P_RANGE')) \
                            .merge(ee.FeatureCollection('users/rfernand387/LANDSAT_LC08_C01_T1_SR/LANDSAT_LC08_C01_T1_SR_SL2P_RANGE')) \
                            .merge(ee.FeatureCollection('users/rfernand387/LANDSAT_LC08_C01_T1_SR/LANDSAT_LC08_C01_T1_SR_SL2P_RANGE')) \
                            .merge(ee.FeatureCollection('users/rfernand387/LANDSAT_LC08_C01_T1_SR/LANDSAT_LC08_C01_T1_SR_SL2P_RANGE')) \
                            .merge(ee.FeatureCollection('users/rfernand387/LANDSAT_LC08_C01_T1_SR/LANDSAT_LC08_C01_T1_SR_SL2P_RANGE')) \
                            .merge(ee.FeatureCollection('users/rfernand387/LANDSAT_LC08_C01_T1_SR/LANDSAT_LC08_C01_T1_SR_SL2P_RANGE')) 

        def l9_createCollection_domains(self):
            return  ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l9_sl2p_weiss_or_prosail_domain') \
            .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l9_sl2p_weiss_or_prosail_domain')) \
            .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l8_sl2p_ROF_sobol_prosail_dbf_big_clumpedv3_domain')) \
            .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l8_sl2p_ROF_sobol_prosail_enf_big_clumpedv2_domain')) \
            .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l9_sl2p_weiss_or_prosail_domain')) \
            .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l9_sl2p_weiss_or_prosail_domain')) \
            .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l9_sl2p_weiss_or_prosail_domain')) \
            .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l8_sl2p_ROF_sobol_prosail_dbf_big_clumpedv3_domain'))\
            .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l9_sl2p_weiss_or_prosail_domain')) \
            .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l9_sl2p_weiss_or_prosail_domain')) \
            .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l9_sl2p_weiss_or_prosail_domain')) \
            .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l8_sl2p_ROF_sobol_prosail_mix_big_clumpedv3_domain')) 




        #--------------------------------------------------------------------------------*/
        # Sentinel 2 Surface_Reflectance CCRS algorithm                                 */                 
        #--------------------------------------------------------------------------------*/
        def s2_createCollection_Network_Ind(self):
          return ee.FeatureCollection('users/rfernand387/Parameter_file_prosail_ccrs_big_clumped2')

        #old version that used 2015 NA land cover
        #def s2_createImageCollection_partition():
        #    return ee.ImageCollection('users/rfernand387/NA_NALCMS_2015_tiles')\
        #              .map(lambda image: image.select("b1").rename("partition") )\
        #              .merge(ee.ImageCollection("COPERNICUS/Landcover/100m/Proba-V/Global")\
        #                        .map( lambda image: image.select("discrete_classification").remap([0,20,30,40,50,60,70,80,90,100,111,112,113,114,115,116,121,122,123,124,125,126,200],[0,8,10,15,17,16,19,18,14,13,1,3,1,5,6,6,2,4,2,5,6,6,18],0).toUint8().rename("partition")))
        #

        #New version using 2020 Na land cover Richard Fernandes Nov 2024
        def s2_createImageCollection_partition(self):
            return ee.ImageCollection(ee.Image('USGS/NLCD_RELEASES/2020_REL/NALCMS'))\
                      .map(lambda image: image.rename("partition") )\
                      .merge(ee.ImageCollection("COPERNICUS/Landcover/100m/Proba-V/Global")\
                                .map( lambda image: image.select("discrete_classification").remap([0,20,30,40,50,60,70,80,90,100,111,112,113,114,115,116,121,122,123,124,125,126,200],[0,8,10,15,17,16,19,18,14,13,1,3,1,5,6,6,2,4,2,5,6,6,18],0).toUint8().rename("partition")))

        def s2_createCollection_legend(self):
            return ee.FeatureCollection('users/rfernand387/Legend_prosail_ccrs_big_clumped')

        def s2_createCollection_estimates(self):
            return  ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/s2_sl2p_weiss_or_prosail_NNT3_Single_0_1') \
            .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/s2_sl2p_weiss_or_prosail_NNT3_Single_0_1')) \
            .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/s2_sl2p_ROF_sobol_prosail_dbf_big_clumped_NNT1_Single_0_1_v2')) \
            .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/s2_sl2p_ROF_sobol_prosail_enf_big_clumped_NNT1_Single_0_1_v2')) \
            .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/s2_sl2p_weiss_or_prosail_NNT3_Single_0_1')) \
            .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/s2_sl2p_weiss_or_prosail_NNT3_Single_0_1')) \
            .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/s2_sl2p_weiss_or_prosail_NNT3_Single_0_1')) \
            .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/s2_sl2p_ROF_sobol_prosail_dbf_big_clumped_NNT1_Single_0_1_v2')) \
            .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/s2_sl2p_weiss_or_prosail_NNT3_Single_0_1')) \
            .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/s2_sl2p_weiss_or_prosail_NNT3_Single_0_1')) \
            .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/s2_sl2p_weiss_or_prosail_NNT3_Single_0_1')) \
            .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/s2_sl2p_ROF_sobol_prosail_mix_big_clumped_NNT1_Single_0_1_v2'))   



        def s2_createCollection_errors(self):
            return   ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/s2_sl2p_weiss_or_prosail_NNT3_Single_0_1_error') \
              .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/s2_sl2p_weiss_or_prosail_NNT3_Single_0_1_error')) \
              .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/s2_sl2p_ROF_sobol_prosail_dbf_big_clumped_NNT1_Single_0_1_v2_errors')) \
              .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/s2_sl2p_ROF_sobol_prosail_enf_big_clumped_NNT1_Single_0_1_v2_errors')) \
              .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/s2_sl2p_weiss_or_prosail_NNT3_Single_0_1_error')) \
              .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/s2_sl2p_weiss_or_prosail_NNT3_Single_0_1_error')) \
              .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/s2_sl2p_weiss_or_prosail_NNT3_Single_0_1_error')) \
              .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/s2_sl2p_ROF_sobol_prosail_dbf_big_clumped_NNT1_Single_0_1_v2_errors')) \
              .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/s2_sl2p_weiss_or_prosail_NNT3_Single_0_1_error')) \
              .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/s2_sl2p_weiss_or_prosail_NNT3_Single_0_1_error')) \
              .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/s2_sl2p_weiss_or_prosail_NNT3_Single_0_1_error')) \
              .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/s2_sl2p_ROF_sobol_prosail_mix_big_clumped_NNT1_Single_0_1_v2_errors'))


        def s2_createCollection_ranges(self):
          return   ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/S2_SL2P_WEISS_ORIGINAL_RANGE') \
            .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/S2_SL2P_WEISS_ORIGINAL_RANGE')) \
            .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/S2_SL2P_WEISS_ORIGINAL_RANGE')) \
            .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/S2_SL2P_WEISS_ORIGINAL_RANGE')) \
            .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/S2_SL2P_WEISS_ORIGINAL_RANGE')) \
            .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/S2_SL2P_WEISS_ORIGINAL_RANGE')) \
            .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/S2_SL2P_WEISS_ORIGINAL_RANGE')) \
            .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/S2_SL2P_WEISS_ORIGINAL_RANGE')) \
            .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/S2_SL2P_WEISS_ORIGINAL_RANGE')) \
            .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/S2_SL2P_WEISS_ORIGINAL_RANGE')) \
            .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/S2_SL2P_WEISS_ORIGINAL_RANGE')) \
            .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/S2_SL2P_WEISS_ORIGINAL_RANGE'))\


        def s2_createCollection_domains(self):
          return   ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/S2_SL2P_WEISS_ORIGINAL_DOMAIN') \
            .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/S2_SL2P_WEISS_ORIGINAL_DOMAIN')) \
            .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/S2_SL2P_WEISS_ORIGINAL_DOMAIN')) \
            .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/S2_SL2P_WEISS_ORIGINAL_DOMAIN')) \
            .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/S2_SL2P_WEISS_ORIGINAL_DOMAIN')) \
            .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/S2_SL2P_WEISS_ORIGINAL_DOMAIN')) \
            .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/S2_SL2P_WEISS_ORIGINAL_DOMAIN')) \
            .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/S2_SL2P_WEISS_ORIGINAL_DOMAIN')) \
            .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/S2_SL2P_WEISS_ORIGINAL_DOMAIN')) \
            .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/S2_SL2P_WEISS_ORIGINAL_DOMAIN')) \
            .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/S2_SL2P_WEISS_ORIGINAL_DOMAIN')) \
            .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/S2_SL2P_WEISS_ORIGINAL_DOMAIN'))






        #--------------------------------------------------------------------------------*/
        # Sentinel 2 Surface_Reflectance 10m CCRS algorithm                                 */                 
        #--------------------------------------------------------------------------------*/
        def s2_10m_createCollection_Network_Ind(self):
          return ee.FeatureCollection('users/rfernand387/Parameter_file_prosail_ccrs_big_clumped2')



        #old version that used 2015 NA land cover
        #def s2_createImageCollection_partition():
        #    return ee.ImageCollection('users/rfernand387/NA_NALCMS_2015_tiles')\
        #              .map(lambda image: image.select("b1").rename("partition") })\
        #              .merge(ee.ImageCollection("COPERNICUS/Landcover/100m/Proba-V/Global")\
        #                        .map( lambda image: image.select("discrete_classification").remap([0,20,30,40,50,60,70,80,90,100,111,112,113,114,115,116,121,122,123,124,125,126,200],[0,8,10,15,17,16,19,18,14,13,1,3,1,5,6,6,2,4,2,5,6,6,18],0).toUint8().rename("partition")))
        #

        #New version using 2020 Na land cover Richard Fernandes Nov 2024
        def s2_10m_createImageCollection_partition(self):
            return ee.ImageCollection(ee.Image('USGS/NLCD_RELEASES/2020_REL/NALCMS'))\
                      .map(lambda image: image.rename("partition") )\
                      .merge(ee.ImageCollection("COPERNICUS/Landcover/100m/Proba-V/Global")\
                                .map( lambda image: image.select("discrete_classification").remap([0,20,30,40,50,60,70,80,90,100,111,112,113,114,115,116,121,122,123,124,125,126,200],[0,8,10,15,17,16,19,18,14,13,1,3,1,5,6,6,2,4,2,5,6,6,18],0).toUint8().rename("partition")))



        def s2_10m_createCollection_legend(self):
            return ee.FeatureCollection('users/rfernand387/Legend_prosail_ccrs_big_clumped')



        def s2_10m_createCollection_estimates(self):

            return  ee.FeatureCollection('users/kateharvey/s2_sl2p_weiss_or_prosail_10m_NNT1_Single_0_1') \
            .merge(ee.FeatureCollection('users/kateharvey/s2_sl2p_weiss_or_prosail_10m_NNT1_Single_0_1')) \
            .merge(ee.FeatureCollection('users/kateharvey/s2_sl2p_weiss_or_prosail_10m_NNT1_Single_0_1')) \
            .merge(ee.FeatureCollection('users/kateharvey/s2_sl2p_weiss_or_prosail_10m_NNT1_Single_0_1')) \
            .merge(ee.FeatureCollection('users/kateharvey/s2_sl2p_weiss_or_prosail_10m_NNT1_Single_0_1')) \
            .merge(ee.FeatureCollection('users/kateharvey/s2_sl2p_weiss_or_prosail_10m_NNT1_Single_0_1')) \
            .merge(ee.FeatureCollection('users/kateharvey/s2_sl2p_weiss_or_prosail_10m_NNT1_Single_0_1')) \
            .merge(ee.FeatureCollection('users/kateharvey/s2_sl2p_weiss_or_prosail_10m_NNT1_Single_0_1')) \
            .merge(ee.FeatureCollection('users/kateharvey/s2_sl2p_weiss_or_prosail_10m_NNT1_Single_0_1')) \
            .merge(ee.FeatureCollection('users/kateharvey/s2_sl2p_weiss_or_prosail_10m_NNT1_Single_0_1')) \
            .merge(ee.FeatureCollection('users/kateharvey/s2_sl2p_weiss_or_prosail_10m_NNT1_Single_0_1')) \
            .merge(ee.FeatureCollection('users/kateharvey/s2_sl2p_weiss_or_prosail_10m_NNT1_Single_0_1')) 



        def s2_10m_createCollection_errors(self):
            return   ee.FeatureCollection('users/kateharvey/s2_sl2p_weiss_or_prosail_10m_NNT1_Single_0_1_errors') \
              .merge(ee.FeatureCollection('users/kateharvey/s2_sl2p_weiss_or_prosail_10m_NNT1_Single_0_1_errors')) \
              .merge(ee.FeatureCollection('users/kateharvey/s2_sl2p_weiss_or_prosail_10m_NNT1_Single_0_1_errors')) \
              .merge(ee.FeatureCollection('users/kateharvey/s2_sl2p_weiss_or_prosail_10m_NNT1_Single_0_1_errors')) \
              .merge(ee.FeatureCollection('users/kateharvey/s2_sl2p_weiss_or_prosail_10m_NNT1_Single_0_1_errors')) \
              .merge(ee.FeatureCollection('users/kateharvey/s2_sl2p_weiss_or_prosail_10m_NNT1_Single_0_1_errors')) \
              .merge(ee.FeatureCollection('users/kateharvey/s2_sl2p_weiss_or_prosail_10m_NNT1_Single_0_1_errors')) \
              .merge(ee.FeatureCollection('users/kateharvey/s2_sl2p_weiss_or_prosail_10m_NNT1_Single_0_1_errors')) \
              .merge(ee.FeatureCollection('users/kateharvey/s2_sl2p_weiss_or_prosail_10m_NNT1_Single_0_1_errors')) \
              .merge(ee.FeatureCollection('users/kateharvey/s2_sl2p_weiss_or_prosail_10m_NNT1_Single_0_1_errors')) \
              .merge(ee.FeatureCollection('users/kateharvey/s2_sl2p_weiss_or_prosail_10m_NNT1_Single_0_1_errors')) \
              .merge(ee.FeatureCollection('users/kateharvey/s2_sl2p_weiss_or_prosail_10m_NNT1_Single_0_1_errors')) 


        def s2_10m_createCollection_ranges(self):
          return   ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/S2_SL2P_WEISS_ORIGINAL_RANGE') \
            .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/S2_SL2P_WEISS_ORIGINAL_RANGE')) \
            .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/S2_SL2P_WEISS_ORIGINAL_RANGE')) \
            .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/S2_SL2P_WEISS_ORIGINAL_RANGE')) \
            .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/S2_SL2P_WEISS_ORIGINAL_RANGE')) \
            .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/S2_SL2P_WEISS_ORIGINAL_RANGE')) \
            .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/S2_SL2P_WEISS_ORIGINAL_RANGE')) \
            .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/S2_SL2P_WEISS_ORIGINAL_RANGE')) \
            .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/S2_SL2P_WEISS_ORIGINAL_RANGE')) \
            .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/S2_SL2P_WEISS_ORIGINAL_RANGE')) \
            .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/S2_SL2P_WEISS_ORIGINAL_RANGE')) \
            .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/S2_SL2P_WEISS_ORIGINAL_RANGE'))


        def s2_10m_createCollection_domains(self):
          return   ee.FeatureCollection('users/kateharvey/s2_sl2p_weiss_or_prosail_10m_domain') \
            .merge(ee.FeatureCollection('users/kateharvey/s2_sl2p_weiss_or_prosail_10m_domain')) \
            .merge(ee.FeatureCollection('users/kateharvey/s2_sl2p_weiss_or_prosail_10m_domain')) \
            .merge(ee.FeatureCollection('users/kateharvey/s2_sl2p_weiss_or_prosail_10m_domain')) \
            .merge(ee.FeatureCollection('users/kateharvey/s2_sl2p_weiss_or_prosail_10m_domain')) \
            .merge(ee.FeatureCollection('users/kateharvey/s2_sl2p_weiss_or_prosail_10m_domain')) \
            .merge(ee.FeatureCollection('users/kateharvey/s2_sl2p_weiss_or_prosail_10m_domain')) \
            .merge(ee.FeatureCollection('users/kateharvey/s2_sl2p_weiss_or_prosail_10m_domain')) \
            .merge(ee.FeatureCollection('users/kateharvey/s2_sl2p_weiss_or_prosail_10m_domain')) \
            .merge(ee.FeatureCollection('users/kateharvey/s2_sl2p_weiss_or_prosail_10m_domain')) \
            .merge(ee.FeatureCollection('users/kateharvey/s2_sl2p_weiss_or_prosail_10m_domain')) \
            .merge(ee.FeatureCollection('users/kateharvey/s2_sl2p_weiss_or_prosail_10m_domain')) 




#--------------------------------------------------------------------------------*/
# Landsat 8 Surface_Reflectance SL2P algoirthm - these are correct RF Nov 2023 */                 
#--------------------------------------------------------------------------------*/
def l8_createCollection_Network_Ind():
  return ee.FeatureCollection('users/rfernand387/Parameter_file_prosail_ccrs_big_clumped2')

#old version that used 2015 NA land cover
# def l8_createImageCollection_partition():
#     return ee.ImageCollection('users/rfernand387/NA_NALCMS_2015_tiles') \
#               .map(lambda image :image.select("b1").rename("partition") ) \
#               .merge(ee.ImageCollection("COPERNICUS/Landcover/100m/Proba-V/Global") \
#                         .map( lambda image :image.select("discrete_classification").remap([0,20,30,40,50,60,70,80,90,100,111,112,113,114,115,116,121,122,123,124,125,126,200],[0,8,10,15,17,16,19,18,14,13,1,3,1,5,6,6,2,4,2,5,6,6,18],0).toUint8().rename("partition")))

def l8_createImageCollection_partition():
    return ee.ImageCollection(ee.Image('USGS/NLCD_RELEASES/2020_REL/NALCMS')) \
              .map(lambda image: image.rename("partition") )\
              .merge(ee.ImageCollection("COPERNICUS/Landcover/100m/Proba-V/Global")\
                        .map( lambda image :image.select("discrete_classification").remap([0,20,30,40,50,60,70,80,90,100,111,112,113,114,115,116,121,122,123,124,125,126,200],[0,8,10,15,17,16,19,18,14,13,1,3,1,5,6,6,2,4,2,5,6,6,18],0).toUint8().rename("partition")))

def l8_createCollection_legend():
    return ee.FeatureCollection('users/rfernand387/Legend_prosail_ccrs_big_clumped')

def l8_createCollection_estimates():
    return  ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l8_sl2p_weiss_or_prosail_NNT1_Single_0_1') \
    .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l8_sl2p_weiss_or_prosail_NNT1_Single_0_1')) \
    .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l8_sl2p_ROF_sobol_prosail_dbf_big_clumpedv3_NNT1_Single_0_1')) \
    .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l8_sl2p_ROF_sobol_prosail_enf_big_clumpedv2_NNT1_Single_0_1')) \
    .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l8_sl2p_weiss_or_prosail_NNT1_Single_0_1')) \
    .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l8_sl2p_weiss_or_prosail_NNT1_Single_0_1')) \
    .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l8_sl2p_weiss_or_prosail_NNT1_Single_0_1')) \
    .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l8_sl2p_ROF_sobol_prosail_dbf_big_clumpedv3_NNT1_Single_0_1')) \
    .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l8_sl2p_weiss_or_prosail_NNT1_Single_0_1')) \
    .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l8_sl2p_weiss_or_prosail_NNT1_Single_0_1')) \
    .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l8_sl2p_weiss_or_prosail_NNT1_Single_0_1')) \
    .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l8_sl2p_ROF_sobol_prosail_mix_big_clumpedv3_NNT1_Single_0_1')) 

def l8_createCollection_errors():
    return  ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l8_sl2p_weiss_or_prosail_NNT1_Single_0_1_incertitudes') \
    .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l8_sl2p_weiss_or_prosail_NNT1_Single_0_1_incertitudes')) \
    .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l8_sl2p_ROF_sobol_prosail_dbf_big_clumpedv3_NNT1_Single_0_1_incertitudes')) \
    .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l8_sl2p_ROF_sobol_prosail_enf_big_clumpedv2_NNT1_Single_0_1_incertitudes')) \
    .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l8_sl2p_weiss_or_prosail_NNT1_Single_0_1_incertitudes')) \
    .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l8_sl2p_weiss_or_prosail_NNT1_Single_0_1_incertitudes')) \
    .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l8_sl2p_weiss_or_prosail_NNT1_Single_0_1_incertitudes')) \
    .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l8_sl2p_ROF_sobol_prosail_dbf_big_clumpedv3_NNT1_Single_0_1_incertitudes')) \
    .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l8_sl2p_weiss_or_prosail_NNT1_Single_0_1_incertitudes')) \
    .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l8_sl2p_weiss_or_prosail_NNT1_Single_0_1_incertitudes')) \
    .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l8_sl2p_weiss_or_prosail_NNT1_Single_0_1_incertitudes')) \
    .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l8_sl2p_ROF_sobol_prosail_mix_big_clumpedv3_NNT1_Single_0_1_incertitudes')) \

def l8_createCollection_ranges():
    return ee.FeatureCollection('users/rfernand387/LANDSAT_LC08_C01_T1_SR/LANDSAT_LC08_C01_T1_SR_SL2P_RANGE')\
                    .merge(ee.FeatureCollection('users/rfernand387/LANDSAT_LC08_C01_T1_SR/LANDSAT_LC08_C01_T1_SR_SL2P_RANGE')) \
                    .merge(ee.FeatureCollection('users/rfernand387/LANDSAT_LC08_C01_T1_SR/LANDSAT_LC08_C01_T1_SR_SL2P_RANGE')) \
                    .merge(ee.FeatureCollection('users/rfernand387/LANDSAT_LC08_C01_T1_SR/LANDSAT_LC08_C01_T1_SR_SL2P_RANGE')) \
                    .merge(ee.FeatureCollection('users/rfernand387/LANDSAT_LC08_C01_T1_SR/LANDSAT_LC08_C01_T1_SR_SL2P_RANGE')) \
                    .merge(ee.FeatureCollection('users/rfernand387/LANDSAT_LC08_C01_T1_SR/LANDSAT_LC08_C01_T1_SR_SL2P_RANGE')) \
                    .merge(ee.FeatureCollection('users/rfernand387/LANDSAT_LC08_C01_T1_SR/LANDSAT_LC08_C01_T1_SR_SL2P_RANGE')) \
                    .merge(ee.FeatureCollection('users/rfernand387/LANDSAT_LC08_C01_T1_SR/LANDSAT_LC08_C01_T1_SR_SL2P_RANGE')) \
                    .merge(ee.FeatureCollection('users/rfernand387/LANDSAT_LC08_C01_T1_SR/LANDSAT_LC08_C01_T1_SR_SL2P_RANGE')) \
                    .merge(ee.FeatureCollection('users/rfernand387/LANDSAT_LC08_C01_T1_SR/LANDSAT_LC08_C01_T1_SR_SL2P_RANGE')) \
                    .merge(ee.FeatureCollection('users/rfernand387/LANDSAT_LC08_C01_T1_SR/LANDSAT_LC08_C01_T1_SR_SL2P_RANGE')) \
                    .merge(ee.FeatureCollection('users/rfernand387/LANDSAT_LC08_C01_T1_SR/LANDSAT_LC08_C01_T1_SR_SL2P_RANGE')) 

def l8_createCollection_domains():
    return  ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l8_sl2p_weiss_or_prosail_domain') \
    .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l8_sl2p_weiss_or_prosail_domain')) \
    .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l8_sl2p_ROF_sobol_prosail_dbf_big_clumpedv3_domain')) \
    .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l8_sl2p_ROF_sobol_prosail_enf_big_clumpedv2_domain')) \
    .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l8_sl2p_weiss_or_prosail_domain')) \
    .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l8_sl2p_weiss_or_prosail_domain')) \
    .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l8_sl2p_weiss_or_prosail_domain')) \
    .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l8_sl2p_ROF_sobol_prosail_dbf_big_clumpedv3_domain')) \
    .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l8_sl2p_weiss_or_prosail_domain')) \
    .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l8_sl2p_weiss_or_prosail_domain')) \
    .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l8_sl2p_weiss_or_prosail_domain')) \
    .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l8_sl2p_ROF_sobol_prosail_mix_big_clumpedv3_domain')) \

#--------------------------------------------------------------------------------*/
# Landsat 9 Surface_Reflectance SL2P algoirthm - these are correct RF Nov 2023 */                 
#--------------------------------------------------------------------------------*/
def l9_createCollection_Network_Ind():
  return ee.FeatureCollection('users/rfernand387/Parameter_file_prosail_ccrs_big_clumped2')


# old version that used 2015 NA land cover
# def l8_createImageCollection_partition():
#     return ee.ImageCollection('users/rfernand387/NA_NALCMS_2015_tiles')\
#               .map(lambda image :image.select("b1").rename("partition") )\
#               .merge(ee.ImageCollection("COPERNICUS/Landcover/100m/Proba-V/Global")\
#                         .map( lambda image :image.select("discrete_classification").remap([0,20,30,40,50,60,70,80,90,100,111,112,113,114,115,116,121,122,123,124,125,126,200],[0,8,10,15,17,16,19,18,14,13,1,3,1,5,6,6,2,4,2,5,6,6,18],0).toUint8().rename("partition")))
# 

def l9_createImageCollection_partition():
    return ee.ImageCollection(ee.Image('USGS/NLCD_RELEASES/2020_REL/NALCMS'))\
              .map(lambda image :image.rename("partition"))\
              .merge(ee.ImageCollection("COPERNICUS/Landcover/100m/Proba-V/Global")\
                        .map( lambda image :image.select("discrete_classification").remap([0,20,30,40,50,60,70,80,90,100,111,112,113,114,115,116,121,122,123,124,125,126,200],[0,8,10,15,17,16,19,18,14,13,1,3,1,5,6,6,2,4,2,5,6,6,18],0).toUint8().rename("partition")))


def l9_createCollection_legend():
    return ee.FeatureCollection('users/rfernand387/Legend_prosail_ccrs_big_clumped')

def l9_createCollection_estimates():
    return  ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l9_sl2p_weiss_or_prosail_NNT1_Single_0_1') \
    .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l9_sl2p_weiss_or_prosail_NNT1_Single_0_1')) \
    .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l8_sl2p_ROF_sobol_prosail_dbf_big_clumpedv3_NNT1_Single_0_1')) \
    .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l8_sl2p_ROF_sobol_prosail_enf_big_clumpedv2_NNT1_Single_0_1')) \
    .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l9_sl2p_weiss_or_prosail_NNT1_Single_0_1')) \
    .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l9_sl2p_weiss_or_prosail_NNT1_Single_0_1')) \
    .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l9_sl2p_weiss_or_prosail_NNT1_Single_0_1')) \
    .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l8_sl2p_ROF_sobol_prosail_dbf_big_clumpedv3_NNT1_Single_0_1')) \
    .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l9_sl2p_weiss_or_prosail_NNT1_Single_0_1')) \
    .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l9_sl2p_weiss_or_prosail_NNT1_Single_0_1')) \
    .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l9_sl2p_weiss_or_prosail_NNT1_Single_0_1')) \
    .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l8_sl2p_ROF_sobol_prosail_mix_big_clumpedv3_NNT1_Single_0_1')) 

def l9_createCollection_errors():
    return  ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l9_sl2p_weiss_or_prosail_NNT1_Single_0_1_incertitudes') \
    .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l9_sl2p_weiss_or_prosail_NNT1_Single_0_1_incertitudes')) \
    .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l8_sl2p_ROF_sobol_prosail_dbf_big_clumpedv3_NNT1_Single_0_1_incertitudes')) \
    .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l8_sl2p_ROF_sobol_prosail_enf_big_clumpedv2_NNT1_Single_0_1_incertitudes')) \
    .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l9_sl2p_weiss_or_prosail_NNT1_Single_0_1_incertitudes')) \
    .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l9_sl2p_weiss_or_prosail_NNT1_Single_0_1_incertitudes')) \
    .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l9_sl2p_weiss_or_prosail_NNT1_Single_0_1_incertitudes')) \
    .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l8_sl2p_ROF_sobol_prosail_dbf_big_clumpedv3_NNT1_Single_0_1_incertitudes')) \
    .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l9_sl2p_weiss_or_prosail_NNT1_Single_0_1_incertitudes')) \
    .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l9_sl2p_weiss_or_prosail_NNT1_Single_0_1_incertitudes')) \
    .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l9_sl2p_weiss_or_prosail_NNT1_Single_0_1_incertitudes')) \
    .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l8_sl2p_ROF_sobol_prosail_mix_big_clumpedv3_NNT1_Single_0_1_incertitudes')) 


def l9_createCollection_ranges():
  return ee.FeatureCollection('users/rfernand387/LANDSAT_LC08_C01_T1_SR/LANDSAT_LC08_C01_T1_SR_SL2P_RANGE')\
                    .merge(ee.FeatureCollection('users/rfernand387/LANDSAT_LC08_C01_T1_SR/LANDSAT_LC08_C01_T1_SR_SL2P_RANGE')) \
                    .merge(ee.FeatureCollection('users/rfernand387/LANDSAT_LC08_C01_T1_SR/LANDSAT_LC08_C01_T1_SR_SL2P_RANGE')) \
                    .merge(ee.FeatureCollection('users/rfernand387/LANDSAT_LC08_C01_T1_SR/LANDSAT_LC08_C01_T1_SR_SL2P_RANGE')) \
                    .merge(ee.FeatureCollection('users/rfernand387/LANDSAT_LC08_C01_T1_SR/LANDSAT_LC08_C01_T1_SR_SL2P_RANGE')) \
                    .merge(ee.FeatureCollection('users/rfernand387/LANDSAT_LC08_C01_T1_SR/LANDSAT_LC08_C01_T1_SR_SL2P_RANGE')) \
                    .merge(ee.FeatureCollection('users/rfernand387/LANDSAT_LC08_C01_T1_SR/LANDSAT_LC08_C01_T1_SR_SL2P_RANGE')) \
                    .merge(ee.FeatureCollection('users/rfernand387/LANDSAT_LC08_C01_T1_SR/LANDSAT_LC08_C01_T1_SR_SL2P_RANGE')) \
                    .merge(ee.FeatureCollection('users/rfernand387/LANDSAT_LC08_C01_T1_SR/LANDSAT_LC08_C01_T1_SR_SL2P_RANGE')) \
                    .merge(ee.FeatureCollection('users/rfernand387/LANDSAT_LC08_C01_T1_SR/LANDSAT_LC08_C01_T1_SR_SL2P_RANGE')) \
                    .merge(ee.FeatureCollection('users/rfernand387/LANDSAT_LC08_C01_T1_SR/LANDSAT_LC08_C01_T1_SR_SL2P_RANGE')) \
                    .merge(ee.FeatureCollection('users/rfernand387/LANDSAT_LC08_C01_T1_SR/LANDSAT_LC08_C01_T1_SR_SL2P_RANGE')) 

def l9_createCollection_domains():
    return  ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l9_sl2p_weiss_or_prosail_domain') \
    .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l9_sl2p_weiss_or_prosail_domain')) \
    .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l8_sl2p_ROF_sobol_prosail_dbf_big_clumpedv3_domain')) \
    .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l8_sl2p_ROF_sobol_prosail_enf_big_clumpedv2_domain')) \
    .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l9_sl2p_weiss_or_prosail_domain')) \
    .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l9_sl2p_weiss_or_prosail_domain')) \
    .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l9_sl2p_weiss_or_prosail_domain')) \
    .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l8_sl2p_ROF_sobol_prosail_dbf_big_clumpedv3_domain'))\
    .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l9_sl2p_weiss_or_prosail_domain')) \
    .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l9_sl2p_weiss_or_prosail_domain')) \
    .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l9_sl2p_weiss_or_prosail_domain')) \
    .merge(ee.FeatureCollection('projects/ee-modis250/assets/SL2P/l8_sl2p_ROF_sobol_prosail_mix_big_clumpedv3_domain')) 




#--------------------------------------------------------------------------------*/
# Sentinel 2 Surface_Reflectance CCRS algorithm                                 */                 
#--------------------------------------------------------------------------------*/
def s2_createCollection_Network_Ind():
  return ee.FeatureCollection('users/rfernand387/Parameter_file_prosail_ccrs_big_clumped2')

#old version that used 2015 NA land cover
#def s2_createImageCollection_partition():
#    return ee.ImageCollection('users/rfernand387/NA_NALCMS_2015_tiles')\
#              .map(lambda image: image.select("b1").rename("partition") )\
#              .merge(ee.ImageCollection("COPERNICUS/Landcover/100m/Proba-V/Global")\
#                        .map( lambda image: image.select("discrete_classification").remap([0,20,30,40,50,60,70,80,90,100,111,112,113,114,115,116,121,122,123,124,125,126,200],[0,8,10,15,17,16,19,18,14,13,1,3,1,5,6,6,2,4,2,5,6,6,18],0).toUint8().rename("partition")))
#

#New version using 2020 Na land cover Richard Fernandes Nov 2024
def s2_createImageCollection_partition():
    return ee.ImageCollection(ee.Image('USGS/NLCD_RELEASES/2020_REL/NALCMS'))\
              .map(lambda image: image.rename("partition") )\
              .merge(ee.ImageCollection("COPERNICUS/Landcover/100m/Proba-V/Global")\
                        .map( lambda image: image.select("discrete_classification").remap([0,20,30,40,50,60,70,80,90,100,111,112,113,114,115,116,121,122,123,124,125,126,200],[0,8,10,15,17,16,19,18,14,13,1,3,1,5,6,6,2,4,2,5,6,6,18],0).toUint8().rename("partition")))

def s2_createCollection_legend():
    return ee.FeatureCollection('users/rfernand387/Legend_prosail_ccrs_big_clumped')

def s2_createCollection_estimates():
    return  ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/s2_sl2p_weiss_or_prosail_NNT3_Single_0_1') \
     .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/s2_sl2p_weiss_or_prosail_NNT3_Single_0_1')) \
     .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/s2_sl2p_ROF_sobol_prosail_dbf_big_clumped_NNT1_Single_0_1_v2')) \
     .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/s2_sl2p_ROF_sobol_prosail_enf_big_clumped_NNT1_Single_0_1_v2')) \
     .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/s2_sl2p_weiss_or_prosail_NNT3_Single_0_1')) \
     .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/s2_sl2p_weiss_or_prosail_NNT3_Single_0_1')) \
     .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/s2_sl2p_weiss_or_prosail_NNT3_Single_0_1')) \
     .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/s2_sl2p_ROF_sobol_prosail_dbf_big_clumped_NNT1_Single_0_1_v2')) \
     .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/s2_sl2p_weiss_or_prosail_NNT3_Single_0_1')) \
     .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/s2_sl2p_weiss_or_prosail_NNT3_Single_0_1')) \
     .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/s2_sl2p_weiss_or_prosail_NNT3_Single_0_1')) \
     .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/s2_sl2p_ROF_sobol_prosail_mix_big_clumped_NNT1_Single_0_1_v2'))   



def s2_createCollection_errors():
    return   ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/s2_sl2p_weiss_or_prosail_NNT3_Single_0_1_error') \
      .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/s2_sl2p_weiss_or_prosail_NNT3_Single_0_1_error')) \
      .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/s2_sl2p_ROF_sobol_prosail_dbf_big_clumped_NNT1_Single_0_1_v2_errors')) \
      .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/s2_sl2p_ROF_sobol_prosail_enf_big_clumped_NNT1_Single_0_1_v2_errors')) \
      .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/s2_sl2p_weiss_or_prosail_NNT3_Single_0_1_error')) \
      .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/s2_sl2p_weiss_or_prosail_NNT3_Single_0_1_error')) \
      .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/s2_sl2p_weiss_or_prosail_NNT3_Single_0_1_error')) \
      .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/s2_sl2p_ROF_sobol_prosail_dbf_big_clumped_NNT1_Single_0_1_v2_errors')) \
      .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/s2_sl2p_weiss_or_prosail_NNT3_Single_0_1_error')) \
      .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/s2_sl2p_weiss_or_prosail_NNT3_Single_0_1_error')) \
      .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/s2_sl2p_weiss_or_prosail_NNT3_Single_0_1_error')) \
      .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/s2_sl2p_ROF_sobol_prosail_mix_big_clumped_NNT1_Single_0_1_v2_errors'))


def s2_createCollection_ranges():
  return   ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/S2_SL2P_WEISS_ORIGINAL_RANGE') \
    .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/S2_SL2P_WEISS_ORIGINAL_RANGE')) \
    .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/S2_SL2P_WEISS_ORIGINAL_RANGE')) \
    .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/S2_SL2P_WEISS_ORIGINAL_RANGE')) \
    .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/S2_SL2P_WEISS_ORIGINAL_RANGE')) \
    .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/S2_SL2P_WEISS_ORIGINAL_RANGE')) \
    .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/S2_SL2P_WEISS_ORIGINAL_RANGE')) \
    .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/S2_SL2P_WEISS_ORIGINAL_RANGE')) \
    .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/S2_SL2P_WEISS_ORIGINAL_RANGE')) \
    .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/S2_SL2P_WEISS_ORIGINAL_RANGE')) \
    .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/S2_SL2P_WEISS_ORIGINAL_RANGE')) \
    .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/S2_SL2P_WEISS_ORIGINAL_RANGE'))\


def s2_createCollection_domains():
  return   ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/S2_SL2P_WEISS_ORIGINAL_DOMAIN') \
    .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/S2_SL2P_WEISS_ORIGINAL_DOMAIN')) \
    .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/S2_SL2P_WEISS_ORIGINAL_DOMAIN')) \
    .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/S2_SL2P_WEISS_ORIGINAL_DOMAIN')) \
    .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/S2_SL2P_WEISS_ORIGINAL_DOMAIN')) \
    .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/S2_SL2P_WEISS_ORIGINAL_DOMAIN')) \
    .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/S2_SL2P_WEISS_ORIGINAL_DOMAIN')) \
    .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/S2_SL2P_WEISS_ORIGINAL_DOMAIN')) \
    .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/S2_SL2P_WEISS_ORIGINAL_DOMAIN')) \
    .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/S2_SL2P_WEISS_ORIGINAL_DOMAIN')) \
    .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/S2_SL2P_WEISS_ORIGINAL_DOMAIN')) \
    .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/S2_SL2P_WEISS_ORIGINAL_DOMAIN'))






#--------------------------------------------------------------------------------*/
# Sentinel 2 Surface_Reflectance 10m CCRS algorithm                                 */                 
#--------------------------------------------------------------------------------*/
def s2_10m_createCollection_Network_Ind():
  return ee.FeatureCollection('users/rfernand387/Parameter_file_prosail_ccrs_big_clumped2')



#old version that used 2015 NA land cover
#def s2_createImageCollection_partition():
#    return ee.ImageCollection('users/rfernand387/NA_NALCMS_2015_tiles')\
#              .map(lambda image: image.select("b1").rename("partition") })\
#              .merge(ee.ImageCollection("COPERNICUS/Landcover/100m/Proba-V/Global")\
#                        .map( lambda image: image.select("discrete_classification").remap([0,20,30,40,50,60,70,80,90,100,111,112,113,114,115,116,121,122,123,124,125,126,200],[0,8,10,15,17,16,19,18,14,13,1,3,1,5,6,6,2,4,2,5,6,6,18],0).toUint8().rename("partition")))
#

#New version using 2020 Na land cover Richard Fernandes Nov 2024
def s2_10m_createImageCollection_partition():
    return ee.ImageCollection(ee.Image('USGS/NLCD_RELEASES/2020_REL/NALCMS'))\
              .map(lambda image: image.rename("partition") )\
              .merge(ee.ImageCollection("COPERNICUS/Landcover/100m/Proba-V/Global")\
                        .map( lambda image: image.select("discrete_classification").remap([0,20,30,40,50,60,70,80,90,100,111,112,113,114,115,116,121,122,123,124,125,126,200],[0,8,10,15,17,16,19,18,14,13,1,3,1,5,6,6,2,4,2,5,6,6,18],0).toUint8().rename("partition")))



def s2_10m_createCollection_legend():
    return ee.FeatureCollection('users/rfernand387/Legend_prosail_ccrs_big_clumped')



def s2_10m_createCollection_estimates():

    return  ee.FeatureCollection('users/kateharvey/s2_sl2p_weiss_or_prosail_10m_NNT1_Single_0_1') \
     .merge(ee.FeatureCollection('users/kateharvey/s2_sl2p_weiss_or_prosail_10m_NNT1_Single_0_1')) \
     .merge(ee.FeatureCollection('users/kateharvey/s2_sl2p_weiss_or_prosail_10m_NNT1_Single_0_1')) \
     .merge(ee.FeatureCollection('users/kateharvey/s2_sl2p_weiss_or_prosail_10m_NNT1_Single_0_1')) \
     .merge(ee.FeatureCollection('users/kateharvey/s2_sl2p_weiss_or_prosail_10m_NNT1_Single_0_1')) \
     .merge(ee.FeatureCollection('users/kateharvey/s2_sl2p_weiss_or_prosail_10m_NNT1_Single_0_1')) \
     .merge(ee.FeatureCollection('users/kateharvey/s2_sl2p_weiss_or_prosail_10m_NNT1_Single_0_1')) \
     .merge(ee.FeatureCollection('users/kateharvey/s2_sl2p_weiss_or_prosail_10m_NNT1_Single_0_1')) \
     .merge(ee.FeatureCollection('users/kateharvey/s2_sl2p_weiss_or_prosail_10m_NNT1_Single_0_1')) \
     .merge(ee.FeatureCollection('users/kateharvey/s2_sl2p_weiss_or_prosail_10m_NNT1_Single_0_1')) \
     .merge(ee.FeatureCollection('users/kateharvey/s2_sl2p_weiss_or_prosail_10m_NNT1_Single_0_1')) \
     .merge(ee.FeatureCollection('users/kateharvey/s2_sl2p_weiss_or_prosail_10m_NNT1_Single_0_1')) 



def s2_10m_createCollection_errors():
    return   ee.FeatureCollection('users/kateharvey/s2_sl2p_weiss_or_prosail_10m_NNT1_Single_0_1_errors') \
      .merge(ee.FeatureCollection('users/kateharvey/s2_sl2p_weiss_or_prosail_10m_NNT1_Single_0_1_errors')) \
      .merge(ee.FeatureCollection('users/kateharvey/s2_sl2p_weiss_or_prosail_10m_NNT1_Single_0_1_errors')) \
      .merge(ee.FeatureCollection('users/kateharvey/s2_sl2p_weiss_or_prosail_10m_NNT1_Single_0_1_errors')) \
      .merge(ee.FeatureCollection('users/kateharvey/s2_sl2p_weiss_or_prosail_10m_NNT1_Single_0_1_errors')) \
      .merge(ee.FeatureCollection('users/kateharvey/s2_sl2p_weiss_or_prosail_10m_NNT1_Single_0_1_errors')) \
      .merge(ee.FeatureCollection('users/kateharvey/s2_sl2p_weiss_or_prosail_10m_NNT1_Single_0_1_errors')) \
      .merge(ee.FeatureCollection('users/kateharvey/s2_sl2p_weiss_or_prosail_10m_NNT1_Single_0_1_errors')) \
      .merge(ee.FeatureCollection('users/kateharvey/s2_sl2p_weiss_or_prosail_10m_NNT1_Single_0_1_errors')) \
      .merge(ee.FeatureCollection('users/kateharvey/s2_sl2p_weiss_or_prosail_10m_NNT1_Single_0_1_errors')) \
      .merge(ee.FeatureCollection('users/kateharvey/s2_sl2p_weiss_or_prosail_10m_NNT1_Single_0_1_errors')) \
      .merge(ee.FeatureCollection('users/kateharvey/s2_sl2p_weiss_or_prosail_10m_NNT1_Single_0_1_errors')) 


def s2_10m_createCollection_ranges():
  return   ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/S2_SL2P_WEISS_ORIGINAL_RANGE') \
    .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/S2_SL2P_WEISS_ORIGINAL_RANGE')) \
    .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/S2_SL2P_WEISS_ORIGINAL_RANGE')) \
    .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/S2_SL2P_WEISS_ORIGINAL_RANGE')) \
    .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/S2_SL2P_WEISS_ORIGINAL_RANGE')) \
    .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/S2_SL2P_WEISS_ORIGINAL_RANGE')) \
    .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/S2_SL2P_WEISS_ORIGINAL_RANGE')) \
    .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/S2_SL2P_WEISS_ORIGINAL_RANGE')) \
    .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/S2_SL2P_WEISS_ORIGINAL_RANGE')) \
    .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/S2_SL2P_WEISS_ORIGINAL_RANGE')) \
    .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/S2_SL2P_WEISS_ORIGINAL_RANGE')) \
    .merge(ee.FeatureCollection('users/rfernand387/COPERNICUS_S2_SR/S2_SL2P_WEISS_ORIGINAL_RANGE'))


def s2_10m_createCollection_domains():
  return   ee.FeatureCollection('users/kateharvey/s2_sl2p_weiss_or_prosail_10m_domain') \
    .merge(ee.FeatureCollection('users/kateharvey/s2_sl2p_weiss_or_prosail_10m_domain')) \
    .merge(ee.FeatureCollection('users/kateharvey/s2_sl2p_weiss_or_prosail_10m_domain')) \
    .merge(ee.FeatureCollection('users/kateharvey/s2_sl2p_weiss_or_prosail_10m_domain')) \
    .merge(ee.FeatureCollection('users/kateharvey/s2_sl2p_weiss_or_prosail_10m_domain')) \
    .merge(ee.FeatureCollection('users/kateharvey/s2_sl2p_weiss_or_prosail_10m_domain')) \
    .merge(ee.FeatureCollection('users/kateharvey/s2_sl2p_weiss_or_prosail_10m_domain')) \
    .merge(ee.FeatureCollection('users/kateharvey/s2_sl2p_weiss_or_prosail_10m_domain')) \
    .merge(ee.FeatureCollection('users/kateharvey/s2_sl2p_weiss_or_prosail_10m_domain')) \
    .merge(ee.FeatureCollection('users/kateharvey/s2_sl2p_weiss_or_prosail_10m_domain')) \
    .merge(ee.FeatureCollection('users/kateharvey/s2_sl2p_weiss_or_prosail_10m_domain')) \
    .merge(ee.FeatureCollection('users/kateharvey/s2_sl2p_weiss_or_prosail_10m_domain')) 


