#include<stdio.h>
#define PI 3.142
int main()
{
	   float radius,area;
	   printf("enter the radius:");
	   scanf("%f",&radius);
	   area=PI*radius*radius;
	   printf("the area of the circle is:%f",area);
	   return 0;
}

