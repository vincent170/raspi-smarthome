# CLS Smart Home Tech Research Club README
> Please read this document before reading our other research documents

## About Us
Hi. We are students based in London in the UK. Our goal is to experiment with house shape, different algorithms, roof type, etc to create an ideal smart home which uses the least energy as possible while heating or cooling the house. 

**Special Mention to the Royal Society Partnership Grant Scheme for sponsoring the project, and our dedicated STEM team leader, Dan Slavinsky for his incredible work.**

## Main Experimenting
- We will primarily be experimenting how the roof pitch (the angle between the sloped part and the base) affects rate of temperature change. Many papers and articles have been written in the past showing how this works, but with limitations such as the location. Not many have tested roof pitch with a real model at all, and also not in UK conditions.
- Our hypothesis is that the flat roof model will heat the fastest due to the smaller volume of air that needs to be heated. 

## What we will be varying:
- Roof shape
- Type of insulation
- The effects of having a roof/doors/windows/walls
- Floor heating vs traditional heating
- PWM cooling algorithms for fans
- Location of furniture

## Roof shape experiment

| Roof shape | Our findings |
|------------|--------------|
| [Flat roof experiment](https://github.com/vincent331/raspi-smarthome/blob/main/experiments/Flatroof.md) | - Adding airflow into a roof, such as using a fan **significantly** increases the rate of temperature increase in a house |
| [No roof experiment](https://github.com/vincent331/raspi-smarthome/blob/main/experiments/Noroof.md) | - Without a roof, warm air escapes the house at a **outstanding** rate, leading to slower heating and faster heat loss - we used this as our control |


## Our code directory

| Name | Description |
|------|-------------|
| [bmetest](https://github.com/vincent331/raspi-smarthome/blob/main/code/tests/bmetest.py) | A program for quickly diagnosing the bme280 sensor which we use to record the temperature. |
| [cmdcontrol](https://github.com/vincent331/raspi-smarthome/blob/main/code/cmdcontrol.py) | A program that allows us to control the sensors using commands and a queue feature |
| [cmdcontrol documentation](https://github.com/vincent331/raspi-smarthome/blob/main/code/codedoc.md) | The documentation for the code above |

## Our construction process
> If you are interested, we recommend replicating this experiment yourself! We'd we excited to hear from your results. Please, make yourself welcome to use our code and our CAD. All CAD files are available below. If you do experiment, don't hesitate to ask us some questions down below or to publish findings to us - we'd love to hear them!
> https://cad.onshape.com/documents/529130551f09940206203912/w/ee31a8500997e97f1aa691da/e/b1a0898e06681da6ed8f3e52
> https://cad.onshape.com/documents/b8587ce09dc4c8c53ae4c49b/w/c211f3e44aa3446b2c8860e3/e/cd3aefbfe74ef3ca53a0623c
> https://cad.onshape.com/documents/33ed95eb90a61a3cb3a3a3ae/w/4272e0742072b9ffce77a9a9/e/05e7c1d25afa338200b83036

| Name | Description |
|------|-------------|
| [Desigining the basic house + construction](https://github.com/vincent331/raspi-smarthome/blob/main/designprocess/Designing%20the%20actual%20house.md) | Documents our design and construction process for the actual house (not roof) and the placements of our measuring instruments for all experiments |

## Contact us
Feel free to contact us if you have any questions, or even new findings.
VincentHao100@hotmail.com - Response within 24 hours
